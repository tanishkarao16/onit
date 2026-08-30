from app.db.database import SessionLocal
from app.models.case import (
    Case as CaseModel,
    CaseActivity,
    CaseStatus,
)
from app.services.case_execution import execute_case


def test_execute_case():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Approved refund action",
            description="Refund action is ready for execution.",
            status=CaseStatus.ACTION_READY,
            approval_required=True,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        result = execute_case(
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

        assert len(activities) == 2

        assert activities[0].event_type == (
            "ACTION_SUBMITTED"
        )

        assert activities[1].event_type == (
            "WAITING_FOR_RESPONSE"
        )

    finally:
        db.close()


def test_execute_case_rejects_wrong_status():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Not ready",
            description="Case is still being analyzed.",
            status=CaseStatus.ANALYZING,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            execute_case(
                db=db,
                case=case,
            )

            assert False, "Expected ValueError"

        except ValueError as exc:
            assert str(exc) == (
                "Case must be ACTION_READY before it can be executed."
            )

    finally:
        db.close()
