import json

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel
from app.services.case_activity import record_activity
from app.services.case_parser import Case as ParsedCase


def persist_parsed_case(
    db: Session,
    parsed_case: ParsedCase,
) -> CaseModel:
    case = CaseModel(
        title=(
            parsed_case.requested_resolution
            or "Parsed case"
        ),
        description=(
            f"Case for {parsed_case.passenger}"
            if parsed_case.passenger
            else "Case parsed from uploaded evidence."
        ),
        passenger=parsed_case.passenger,
        booking_reference=parsed_case.booking_reference,
        organization=parsed_case.airline,
        airline=parsed_case.airline,
        cancellation_date=parsed_case.cancellation_date,
        amount=parsed_case.amount,
        refund_received=parsed_case.refund_received,
        requested_resolution=parsed_case.requested_resolution,
        supporting_facts=json.dumps(
            parsed_case.supporting_facts or []
        ),
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="CASE_CREATED",
        message="Case created from submitted evidence.",
    )

    return case
