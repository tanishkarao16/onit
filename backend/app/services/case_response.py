from sqlalchemy.orm import Session

from app.models.case import (
    Case as CaseModel,
    CaseResponse,
    CaseStatus,
)
from app.services.case_activity import record_activity


def record_case_response(
    db: Session,
    case: CaseModel,
    response_type: str,
    message: str,
    resolved: bool = False,
) -> CaseResponse:
    """
    Record a response from the external organization.

    A response may arrive immediately after submission or while
    the case is waiting for a response.

    SUBMITTED / WAITING_FOR_RESPONSE
        -> RESOLVED
        -> FOLLOW_UP_REQUIRED
    """

    if case.status not in (
        CaseStatus.SUBMITTED,
        CaseStatus.WAITING_FOR_RESPONSE,
    ):
        raise ValueError(
            "Case must be submitted or waiting for a response "
            "before a response can be recorded."
        )

    response = CaseResponse(
        case_id=case.id,
        response_type=response_type,
        message=message,
        resolved=resolved,
    )

    db.add(response)

    if case.status == CaseStatus.SUBMITTED:
        case.status = CaseStatus.WAITING_FOR_RESPONSE

    db.commit()
    db.refresh(response)
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="RESPONSE_RECEIVED",
        message="ONIT received a response from the external organization.",
    )

    if resolved:
        case.status = CaseStatus.RESOLVED
        event_type = "CASE_RESOLVED"
        activity_message = (
            "External response resolved the case."
        )
    else:
        case.status = CaseStatus.FOLLOW_UP_REQUIRED
        event_type = "FOLLOW_UP_REQUIRED"
        activity_message = (
            "External response requires further action."
        )

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type=event_type,
        message=activity_message,
    )

    return response


def send_case_follow_up(
    db: Session,
    case: CaseModel,
) -> CaseModel:
    """
    Send a follow-up action for a case requiring further action.

    FOLLOW_UP_REQUIRED -> WAITING_FOR_RESPONSE
    """

    if case.status != CaseStatus.FOLLOW_UP_REQUIRED:
        raise ValueError(
            "Case must require follow-up before a follow-up can be sent."
        )

    case.status = CaseStatus.WAITING_FOR_RESPONSE

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="FOLLOW_UP_SENT",
        message=(
            "ONIT sent a follow-up to the external organization "
            "and is waiting for a response."
        ),
    )

    return case
