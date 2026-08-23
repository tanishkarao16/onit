from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity
from app.services.case_activity import record_activity


def test_record_case_activity():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a refund.",
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        activity = record_activity(
            db=db,
            case_id=case.id,
            event_type="CASE_CREATED",
            message="Case created from submitted evidence.",
        )

        assert activity.id is not None
        assert activity.case_id == case.id
        assert activity.event_type == "CASE_CREATED"
        assert activity.message == "Case created from submitted evidence."

        stored = db.get(CaseActivity, activity.id)

        assert stored is not None
        assert stored.case_id == case.id
        assert stored.event_type == "CASE_CREATED"

    finally:
        db.close()
