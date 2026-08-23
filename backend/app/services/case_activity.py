from sqlalchemy.orm import Session

from app.models.case import CaseActivity


def record_activity(
    db: Session,
    case_id: int,
    event_type: str,
    message: str,
) -> CaseActivity:
    activity = CaseActivity(
        case_id=case_id,
        event_type=event_type,
        message=message,
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity
