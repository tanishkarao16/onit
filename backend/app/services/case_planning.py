import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseStatus
from app.services.case_activity import record_activity
from app.services.case_decision import CaseDecision


@dataclass
class CasePlan:
    summary: str
    steps: list[str]
    approval_required: bool


def build_case_plan(decision: CaseDecision) -> CasePlan:
    """
    Convert ONIT's case decision into a concrete execution plan.

    This first version is deterministic so it is cheap, testable,
    and predictable.
    """

    if decision.recommended_action == "Request the full refund from the airline":
        return CasePlan(
            summary="Prepare and submit a full refund request to the airline.",
            steps=[
                "Verify the cancellation and refund evidence.",
                "Prepare a refund request using the case details.",
                "Attach the supporting evidence.",
                "Submit the refund request to the airline.",
                "Track the airline's response.",
                "Follow up if the refund is not received within the expected timeframe.",
            ],
            approval_required=True,
        )

    return CasePlan(
        summary="Review the case and determine the appropriate next action.",
        steps=[
            "Review the available case evidence.",
            "Determine the appropriate resolution.",
            "Prepare the required action.",
        ],
        approval_required=True,
    )


def plan_case(
    db: Session,
    case: CaseModel,
    decision: CaseDecision,
) -> CasePlan:
    """
    Generate and persist an execution plan for a case.
    """

    case.status = CaseStatus.PLANNING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_STARTED",
        message="ONIT started building an execution plan.",
    )

    plan = build_case_plan(decision)

    case.plan_summary = plan.summary
    case.plan_steps = json.dumps(plan.steps)
    case.approval_required = plan.approval_required
    case.status = CaseStatus.ACTION_READY

    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PLANNING_COMPLETED",
        message=(
            f"ONIT created an execution plan with "
            f"{len(plan.steps)} steps."
        ),
    )

    return plan
