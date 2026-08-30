from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseStatus
from app.services.case_activity import record_activity


def execute_case(
    db: Session,
    case: CaseModel,
) -> CaseModel:
    """
    Execute the prepared action.

    ACTION_READY is the execution gate:
    - Cases that do not require approval may reach ACTION_READY directly.
    - Cases requiring approval reach ACTION_READY only after
      explicit user approval.

    For the current MVP, execution records the submission and moves
    the case into response-tracking.
    """

    if case.status != CaseStatus.ACTION_READY:
        raise ValueError(
            "Case must be ACTION_READY before it can be executed."
        )

    case.status = CaseStatus.SUBMITTED

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="ACTION_SUBMITTED",
        message=(
            "ONIT submitted the prepared action after user approval."
        ),
    )

    case.status = CaseStatus.WAITING_FOR_RESPONSE

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="WAITING_FOR_RESPONSE",
        message=(
            "ONIT is waiting for the external organization to respond."
        ),
    )

    return case
