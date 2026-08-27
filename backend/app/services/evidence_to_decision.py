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
from app.services.case_decision import decide_case, CaseDecision
from app.services.case_planning import build_case_plan, plan_case


def synthesize_evidence_and_plan(db: Session, case: CaseModel) -> dict:
    """
    Synthesize persisted CaseResearch into a decision and execution plan.

    - Reads persisted CaseResearch rows
    - Calls the deterministic decision logic
    - Augments the decision with evidence references
    - Builds a plan and persists it
    - Records activity events
    Returns a summary dict for tests and APIs.
    """

    record_activity(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_SYNTHESIS_STARTED",
        message="ONIT started synthesizing evidence into a decision.",
    )

    # gather evidence
    items: List[CaseResearch] = (
        db.query(CaseResearch)
        .filter(CaseResearch.case_id == case.id)
        .order_by(CaseResearch.created_at.asc())
        .all()
    )

    if not items:
        record_activity(
            db=db,
            case_id=case.id,
            event_type="EVIDENCE_INSUFFICIENT",
            message="Insufficient evidence to synthesize a decision.",
        )
        # leave status as EVIDENCE_READY
        raise ValueError("Insufficient evidence to synthesize decision")

    # build an evidence summary and check for authoritative sources
    evidence_refs = []
    authoritative = False
    for it in items:
        evidence_refs.append({"source": it.source, "title": it.title, "url": it.url, "relevance": it.relevance})
        lnk = (it.url or "").lower()
        if it.relevance and it.relevance.lower() == "high":
            authoritative = True
        if lnk and (".gov" in lnk or ".gov." in lnk):
            authoritative = True

    # Use existing decision logic based on parsed case
    parsed = ParsedCase(
        passenger=case.passenger,
        booking_reference=case.booking_reference,
        airline=case.airline,
        cancellation_date=case.cancellation_date,
        amount=case.amount,
        refund_received=case.refund_received,
        requested_resolution=case.requested_resolution,
        supporting_facts=json.loads(case.supporting_facts or "[]"),
    )

    decision: CaseDecision = decide_case(parsed)

    # Augment reason with evidence summary
    evidence_texts = [f"{e['source']} ({e['url']})" if e.get("url") else e["source"] for e in evidence_refs]
    decision_reason = f"{decision.reason}\n\nEvidence: {', '.join(evidence_texts)}"

    # Persist decision into case
    case.issue = decision.issue
    case.recommended_action = decision.recommended_action
    case.priority = decision.priority
    case.decision_reason = decision_reason

    record_activity(
        db=db,
        case_id=case.id,
        event_type="DECISION_MADE",
        message=(
            f"ONIT made a decision: {decision.issue}. Recommended: {decision.recommended_action}."
        ),
    )

    # Build plan
    plan = build_case_plan(decision)

    # If authoritative evidence exists, allow auto-action (no approval required)
    if authoritative:
        plan.approval_required = False

    # Persist plan (mirror plan_case behavior but respect our approval override)
    case.status = CaseStatus.PLANNING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_STARTED",
        message="ONIT started building an execution plan.",
    )

    case.plan_summary = plan.summary
    case.plan_steps = json.dumps(plan.steps)
    case.approval_required = plan.approval_required
    case.status = CaseStatus.ACTION_READY if not plan.approval_required else CaseStatus.AWAITING_APPROVAL

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_COMPLETED",
        message=(
            f"ONIT created an execution plan with {len(plan.steps)} steps."
        ),
    )

    record_activity(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_SYNTHESIS_COMPLETED",
        message=(f"ONIT synthesized evidence and produced a plan ({len(plan.steps)} steps)."),
    )

    return {
        "issue": case.issue,
        "recommended_action": case.recommended_action,
        "priority": case.priority,
        "decision_reason": case.decision_reason,
        "plan_summary": case.plan_summary,
        "plan_steps": json.loads(case.plan_steps or "[]"),
        "approval_required": case.approval_required,
        "status": case.status,
        "evidence": evidence_refs,
    }
