import json

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseStatus
from app.services.case_decision import CaseDecision
from app.services.case_planning import build_case_plan, plan_case


REFUND_ISSUE = "Cancelled flight with refund not received"

REFUND_ACTION = (
    "Verify the passenger's refund eligibility, "
    "contact the airline to request the applicable "
    "refund, and follow up until a response is received."
)


def test_build_refund_plan():
    decision = CaseDecision(
        issue=REFUND_ISSUE,
        recommended_action=REFUND_ACTION,
        priority="high",
        reason=(
            "The available case information indicates "
            "that a flight was cancelled and the passenger "
            "has not received the expected refund."
        ),
    )

    plan = build_case_plan(decision)

    assert plan.summary == (
        "Prepare and pursue the passenger's applicable "
        "refund request with the airline."
    )

    assert len(plan.steps) == 7

    assert plan.steps[0] == (
        "Verify the flight cancellation and supporting evidence."
    )

    assert plan.steps[1] == (
        "Verify the passenger's refund eligibility."
    )

    assert plan.steps[2] == (
        "Prepare a refund request using the case details."
    )

    assert plan.steps[3] == (
        "Attach the supporting evidence."
    )

    assert plan.steps[4] == (
        "Contact the airline and submit the applicable refund request."
    )

    assert plan.steps[5] == (
        "Track the airline's response."
    )

    assert plan.steps[6] == (
        "Follow up if the airline does not respond or the refund is not received."
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
            issue=REFUND_ISSUE,
            recommended_action=REFUND_ACTION,
            priority="high",
            reason="The passenger has not received the expected refund.",
        )

        plan = plan_case(
            db=db,
            case=case,
            decision=decision,
        )

        assert plan.approval_required is True

        # Since the plan requires human approval,
        # ONIT should stop before execution.
        assert case.status == CaseStatus.AWAITING_APPROVAL

        assert case.plan_summary == (
            "Prepare and pursue the passenger's applicable "
            "refund request with the airline."
        )

        assert case.approval_required is True

        steps = json.loads(case.plan_steps)

        assert len(steps) == 7

        assert steps[0] == (
            "Verify the flight cancellation and supporting evidence."
        )

        assert steps[1] == (
            "Verify the passenger's refund eligibility."
        )

        assert steps[4] == (
            "Contact the airline and submit the applicable refund request."
        )

        assert steps[-1] == (
            "Follow up if the airline does not respond or the refund is not received."
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

        assert activities[0].message == (
            "ONIT started building an execution plan."
        )

        assert activities[1].event_type == "PLANNING_COMPLETED"

        assert activities[1].message == (
            "ONIT created an execution plan with 7 steps."
        )

    finally:
        db.close()
