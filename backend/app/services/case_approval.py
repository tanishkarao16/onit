from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseStatus
from app.services.case_activity import record_activity


def request_case_approval(
    db: Session,
    case: CaseModel,
) -> CaseModel:
    """
    Move an action-ready case into the approval state.

    ONIT must receive explicit user approval before any external
    action is executed.
    """

    if case.status != CaseStatus.ACTION_READY:
        raise ValueError(
            "Case must be ACTION_READY before approval can be requested."
        )

    case.status = CaseStatus.AWAITING_APPROVAL
    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="APPROVAL_REQUESTED",
        message="ONIT prepared the action and is awaiting user approval.",
    )

    return case
