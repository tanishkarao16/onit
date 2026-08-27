from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseStatus
from app.services.case_approval import request_case_approval, approve_case


def test_request_case_approval():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a full refund.",
            passenger="Alex Morgan",
            booking_reference="ABC123",
            organization="Example Airways",
            airline="Example Airways",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            status=CaseStatus.ACTION_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        result = request_case_approval(
            db=db,
            case=case,
        )

        assert result.status == CaseStatus.AWAITING_APPROVAL

        activities = (
            db.query(CaseActivity)
            .filter(CaseActivity.case_id == case.id)
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 1
        assert activities[0].event_type == "APPROVAL_REQUESTED"
        assert activities[0].message == (
            "ONIT prepared the action and is awaiting user approval."
        )

    finally:
        db.close()


def test_approve_case():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Awaiting approval",
            description="Ready for approval",
            status=CaseStatus.AWAITING_APPROVAL,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        result = approve_case(db=db, case=case)

        assert result.status == CaseStatus.ACTION_READY

        activities = (
            db.query(CaseActivity)
            .filter(CaseActivity.case_id == case.id)
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 1
        assert activities[0].event_type == "APPROVAL_GRANTED"
        assert "approved" in activities[0].message.lower()

    finally:
        db.close()


def test_request_case_approval_rejects_wrong_status():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Unready case",
            description="Case is not ready for approval.",
            status=CaseStatus.CREATED,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            request_case_approval(
                db=db,
                case=case,
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert str(exc) == (
                "Case must be ACTION_READY before approval can be requested."
            )

    finally:
        db.close()
