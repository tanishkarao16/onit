import json

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseStatus
from app.services.case_activity import record_activity
from app.services.case_decision import CaseDecision, decide_case
from app.services.case_parser import Case as ParsedCase


def analyze_case(
    db: Session,
    case: CaseModel,
) -> CaseDecision:
    case.status = CaseStatus.ANALYZING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="ANALYSIS_STARTED",
        message="ONIT started analyzing the case.",
    )

    parsed_case = ParsedCase(
        passenger=case.passenger,
        booking_reference=case.booking_reference,
        airline=case.airline,
        cancellation_date=case.cancellation_date,
        amount=case.amount,
        refund_received=case.refund_received,
        requested_resolution=case.requested_resolution,
        supporting_facts=json.loads(case.supporting_facts or "[]"),
    )

    decision = decide_case(parsed_case)

    case.issue = decision.issue
    case.recommended_action = decision.recommended_action
    case.priority = decision.priority
    case.decision_reason = decision.reason
    case.status = CaseStatus.EVIDENCE_READY

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="ANALYSIS_COMPLETED",
        message=(
            f"ONIT identified: {decision.issue}. "
            f"Recommended action: {decision.recommended_action}."
        ),
    )

    return decision
