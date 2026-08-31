import json
from typing import List

from sqlalchemy.orm import Session

from app.models.case import (
    Case as CaseModel,
    CaseResearch,
    CaseStatus,
)
from app.services.case_activity import record_activity
from app.services.case_parser import Case as ParsedCase
from app.services.case_decision import decide_case
from app.services.case_planning import build_case_plan


def _compute_evidence_strength(
    items: List[CaseResearch],
) -> str:
    if not items:
        return "insufficient"

    high = sum(
        1
        for item in items
        if (item.relevance or "").lower() == "high"
    )

    if high >= 2:
        return "strong"

    if high >= 1 or len(items) >= 3:
        return "moderate"

    return "insufficient"


def _compute_confidence(
    items: List[CaseResearch],
) -> int:
    if not items:
        return 0

    score = 50

    high = sum(
        1
        for item in items
        if (item.relevance or "").lower() == "high"
    )

    score += min(high * 10, 30)

    authoritative = sum(
        1
        for item in items
        if item.url and ".gov" in item.url.lower()
    )

    score += min(authoritative * 5, 10)

    if len(items) >= 5:
        score += 5
    elif len(items) >= 3:
        score += 3

    return max(0, min(100, score))


def _classify_evidence_stance(
    items: List[CaseResearch],
) -> dict:
    supporting = 0
    conflicting = 0
    uncertain = 0

    for item in items:
        url = (item.url or "").lower()
        source = (item.source or "").lower()
        relevance = (item.relevance or "").lower()

        if relevance == "high":
            if ".gov" in url or "official" in source:
                supporting += 1
            else:
                uncertain += 1
        elif relevance == "medium":
            uncertain += 1
        else:
            uncertain += 1

    return {
        "supporting": supporting,
        "conflicting": conflicting,
        "uncertain": uncertain,
        "total": len(items),
    }


def synthesize_evidence_and_plan(
    db: Session,
    case: CaseModel,
) -> dict:
    """
    Convert persisted external research into an evidence-backed
    decision and execution plan.

    ONIT's safety rule:

        Research -> Decision -> Plan -> Human Approval

    External evidence NEVER bypasses human approval.
    """

    record_activity(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_SYNTHESIS_STARTED",
        message=(
            "ONIT started synthesizing evidence into a decision."
        ),
    )

    # --------------------------------------------------------
    # LOAD RESEARCH
    # --------------------------------------------------------

    items: List[CaseResearch] = (
        db.query(CaseResearch)
        .filter(
            CaseResearch.case_id == case.id
        )
        .order_by(
            CaseResearch.created_at.asc()
        )
        .all()
    )

    if not items:
        record_activity(
            db=db,
            case_id=case.id,
            event_type="EVIDENCE_INSUFFICIENT",
            message=(
                "Insufficient external evidence to "
                "synthesize a decision."
            ),
        )

        case.status = CaseStatus.EVIDENCE_READY
        db.commit()

        raise ValueError(
            "Insufficient evidence to synthesize decision"
        )

    # --------------------------------------------------------
    # BUILD EVIDENCE REFERENCES
    # --------------------------------------------------------

    evidence_refs = []

    for item in items:
        evidence_refs.append(
            {
                "source": item.source,
                "title": item.title,
                "url": item.url,
                "relevance": item.relevance,
            }
        )

    # --------------------------------------------------------
    # BUILD PARSED CASE
    # --------------------------------------------------------

    supporting_facts = []

    if case.supporting_facts:
        try:

            loaded = json.loads(
                case.supporting_facts
            )

            if isinstance(
                loaded,
                list,
            ):
                supporting_facts = loaded

            elif isinstance(
                loaded,
                str,
            ):
                supporting_facts = [
                    loaded
                ]

        except (
            TypeError,
            json.JSONDecodeError,
        ):

            supporting_facts = [
                str(
                    case.supporting_facts
                )
            ]

    parsed = ParsedCase(
        passenger=case.passenger,
        booking_reference=case.booking_reference,
        airline=case.airline,
        cancellation_date=case.cancellation_date,
        flight_number=getattr(
            case,
            "flight_number",
            None,
        ),
        amount=case.amount,
        amount_value=getattr(
            case,
            "amount_value",
            None,
        ),
        amount_currency=getattr(
            case,
            "amount_currency",
            None,
        ),
        refund_received=case.refund_received,
        requested_resolution=case.requested_resolution,
        supporting_facts=supporting_facts,
    )

    # Support manually created cases.
    parsed.description = (
        case.description or ""
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    decision = decide_case(parsed)

    # --------------------------------------------------------
    # EVIDENCE-AWARE REASON
    # --------------------------------------------------------

    evidence_lines = []

    for ref in evidence_refs:
        source = ref.get("source") or "Unknown source"
        title = ref.get("title") or "Untitled source"
        url = ref.get("url")

        if url:
            evidence_lines.append(
                f"{source}: {title} ({url})"
            )
        else:
            evidence_lines.append(
                f"{source}: {title}"
            )

    evidence_text = "\n".join(
        f"- {line}"
        for line in evidence_lines
    )

    decision_reason = (
        f"{decision.reason}\n\n"
        "Supporting research:\n"
        f"{evidence_text}"
    )

    # --------------------------------------------------------
    # PERSIST DECISION
    # --------------------------------------------------------

    case.issue = decision.issue
    case.recommended_action = (
        decision.recommended_action
    )
    case.priority = decision.priority
    case.decision_reason = decision_reason

    record_activity(
        db=db,
        case_id=case.id,
        event_type="DECISION_MADE",
        message=(
            f"ONIT made a decision: "
            f"{decision.issue}. "
            f"Recommended action: "
            f"{decision.recommended_action}."
        ),
    )

    # --------------------------------------------------------
    # BUILD EXECUTION PLAN
    # --------------------------------------------------------

    plan = build_case_plan(decision)

    case.status = CaseStatus.PLANNING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_STARTED",
        message=(
            "ONIT started building an execution plan."
        ),
    )

    case.plan_summary = plan.summary

    case.plan_steps = json.dumps(
        plan.steps
    )

    # --------------------------------------------------------
    # IMPORTANT SAFETY RULE
    # --------------------------------------------------------
    #
    # Research must NEVER automatically authorize
    # an external action.
    #
    # Even if:
    #   - the source is .gov
    #   - the source is official
    #   - evidence is strong
    #
    # the user must approve the action.
    #

    case.approval_required = True

    case.status = (
        CaseStatus.AWAITING_APPROVAL
    )

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_COMPLETED",
        message=(
            f"ONIT created an execution plan "
            f"with {len(plan.steps)} steps. "
            "Human approval is required before execution."
        ),
    )

    record_activity(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_SYNTHESIS_COMPLETED",
        message=(
            "ONIT synthesized the available evidence "
            "into a decision and execution plan."
        ),
    )

    evidence_strength = (
        _compute_evidence_strength(items)
    )

    confidence = _compute_confidence(items)
    stance = _classify_evidence_stance(items)

    return {
        "issue": case.issue,
        "recommended_action": (
            case.recommended_action
        ),
        "priority": case.priority,
        "decision_reason": (
            case.decision_reason
        ),
        "plan_summary": case.plan_summary,
        "plan_steps": json.loads(
            case.plan_steps or "[]"
        ),
        "approval_required": True,
        "status": case.status,
        "evidence": evidence_refs,
        "evidence_strength": evidence_strength,
        "confidence": confidence,
        "stance": stance,
    }
