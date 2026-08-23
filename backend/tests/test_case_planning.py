import json

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseStatus
from app.services.case_decision import CaseDecision
from app.services.case_planning import build_case_plan, plan_case


def test_build_refund_plan():
    decision = CaseDecision(
        issue="Cancelled flight with refund not received",
        recommended_action="Request the full refund from the airline",
        priority="high",
        reason="Refund has not been received.",
    )

    plan = build_case_plan(decision)

    assert plan.summary == (
        "Prepare and submit a full refund request to the airline."
    )

    assert len(plan.steps) == 6
    assert plan.steps[0] == (
        "Verify the cancellation and refund evidence."
    )
    assert plan.steps[-1] == (
        "Follow up if the refund is not received within the expected timeframe."
    )

    assert plan.approval_required is True


def test_plan_case_persists_plan_and_activity():
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

        decision = CaseDecision(
            issue="Cancelled flight with refund not received",
            recommended_action="Request the full refund from the airline",
            priority="high",
            reason="Refund has not been received.",
        )

        plan = plan_case(
            db=db,
            case=case,
            decision=decision,
        )

        assert plan.approval_required is True

        assert case.status == CaseStatus.ACTION_READY

        assert case.plan_summary == (
            "Prepare and submit a full refund request to the airline."
        )

        assert case.approval_required is True

        steps = json.loads(case.plan_steps)

        assert len(steps) == 6
        assert steps[0] == (
            "Verify the cancellation and refund evidence."
        )

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

        assert activities[0].event_type == "PLANNING_STARTED"

        assert activities[1].event_type == "PLANNING_COMPLETED"

    finally:
        db.close()
