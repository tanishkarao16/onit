from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseResearch, CaseStatus
from app.services.case_research import research_case


def test_research_case_persists_results_and_activity():
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
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        results = research_case(
            db=db,
            case=case,
        )

        assert len(results) == 1

        assert results[0].source == "Example Airways"
        assert results[0].title == (
            "Case-specific refund policy research"
        )

        assert case.status == CaseStatus.EVIDENCE_READY

        stored = (
            db.query(CaseResearch)
            .filter(CaseResearch.case_id == case.id)
            .all()
        )

        assert len(stored) == 1
        assert stored[0].source == "Example Airways"

        activities = (
            db.query(CaseActivity)
            .filter(CaseActivity.case_id == case.id)
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 2

        assert activities[0].event_type == "RESEARCH_STARTED"
        assert activities[1].event_type == "RESEARCH_COMPLETED"

    finally:
        db.close()
