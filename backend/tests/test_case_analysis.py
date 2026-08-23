from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseStatus
from app.services.case_analysis import analyze_case


def test_analyze_case_persists_decision_and_activity():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a full refund.",
            passenger="Alex Morgan",
            booking_reference="ABC123",
            organization="Example Airways",
            airline="Example Airways",
            cancellation_date="August 1, 2026",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            supporting_facts='["Refund received: No"]',
            status=CaseStatus.CREATED,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        decision = analyze_case(db, case)

        assert decision.issue == "Cancelled flight with refund not received"
        assert decision.recommended_action == (
            "Request the full refund from the airline"
        )
        assert decision.priority == "high"

        assert case.status == CaseStatus.EVIDENCE_READY
        assert case.issue == "Cancelled flight with refund not received"
        assert case.recommended_action == (
            "Request the full refund from the airline"
        )
        assert case.priority == "high"
        assert "Y120,000" in case.decision_reason

        activities = (
            db.query(CaseActivity)
            .filter(CaseActivity.case_id == case.id)
            .order_by(CaseActivity.created_at.asc(), CaseActivity.id.asc())
            .all()
        )

        assert len(activities) == 2

        assert activities[0].event_type == "ANALYSIS_STARTED"
        assert activities[0].message == (
            "ONIT started analyzing the case."
        )

        assert activities[1].event_type == "ANALYSIS_COMPLETED"
        assert "Cancelled flight with refund not received" in (
            activities[1].message
        )
        assert "Request the full refund from the airline" in (
            activities[1].message
        )

    finally:
        db.close()
