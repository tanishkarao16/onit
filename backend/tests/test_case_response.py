from app.db.database import SessionLocal
from app.models.case import (
    Case as CaseModel,
    CaseActivity,
    CaseResponse,
    CaseStatus,
)
from app.services.case_response import (
    record_case_response,
    send_case_follow_up,
)


def test_resolved_response_marks_case_resolved():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Refund response",
            description="Waiting for airline response.",
            status=CaseStatus.WAITING_FOR_RESPONSE,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        response = record_case_response(
            db=db,
            case=case,
            response_type="REFUND_APPROVED",
            message="Airline confirmed the refund.",
            resolved=True,
        )

        assert response.resolved is True
        assert response.response_type == "REFUND_APPROVED"
        assert response.message == "Airline confirmed the refund."

        db.refresh(case)

        assert case.status == CaseStatus.RESOLVED

        activities = (
            db.query(CaseActivity)
            .filter(
                CaseActivity.case_id == case.id
            )
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 2

        assert activities[0].event_type == (
            "RESPONSE_RECEIVED"
        )

        assert activities[1].event_type == (
            "CASE_RESOLVED"
        )

    finally:
        db.close()


def test_unresolved_response_requires_follow_up():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Refund follow-up",
            description="Airline response requires follow-up.",
            status=CaseStatus.WAITING_FOR_RESPONSE,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        response = record_case_response(
            db=db,
            case=case,
            response_type="MORE_INFORMATION_REQUIRED",
            message="Airline requested additional documents.",
            resolved=False,
        )

        assert response.resolved is False

        db.refresh(case)

        assert case.status == (
            CaseStatus.FOLLOW_UP_REQUIRED
        )

        activities = (
            db.query(CaseActivity)
            .filter(
                CaseActivity.case_id == case.id
            )
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 2

        assert activities[0].event_type == (
            "RESPONSE_RECEIVED"
        )

        assert activities[1].event_type == (
            "FOLLOW_UP_REQUIRED"
        )

    finally:
        db.close()


def test_follow_up_returns_case_to_waiting():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Follow-up case",
            description="A follow-up is required.",
            status=CaseStatus.FOLLOW_UP_REQUIRED,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        result = send_case_follow_up(
            db=db,
            case=case,
        )

        assert result.status == (
            CaseStatus.WAITING_FOR_RESPONSE
        )

        activities = (
            db.query(CaseActivity)
            .filter(
                CaseActivity.case_id == case.id
            )
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 1

        assert activities[0].event_type == (
            "FOLLOW_UP_SENT"
        )

    finally:
        db.close()


def test_response_rejects_case_that_has_not_been_submitted():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Not submitted",
            description="Case is still being researched.",
            status=CaseStatus.RESEARCHING,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            record_case_response(
                db=db,
                case=case,
                response_type="UNKNOWN",
                message="Response",
                resolved=False,
            )

            assert False, "Expected ValueError"

        except ValueError as exc:
            assert str(exc) == (
                "Case must be submitted or waiting for a response "
                "before a response can be recorded."
            )

    finally:
        db.close()


def test_follow_up_rejects_case_not_requiring_follow_up():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="No follow-up",
            description="Still waiting normally.",
            status=CaseStatus.WAITING_FOR_RESPONSE,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            send_case_follow_up(
                db=db,
                case=case,
            )

            assert False, "Expected ValueError"

        except ValueError as exc:
            assert str(exc) == (
                "Case must require follow-up before a follow-up can be sent."
            )

    finally:
        db.close()
