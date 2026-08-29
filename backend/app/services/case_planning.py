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

    Planning is based on the meaning of the decision rather than
    requiring one exact recommended-action sentence.
    """

    issue = (decision.issue or "").lower()
    action = (decision.recommended_action or "").lower()

    # ========================================================
    # CANCELLED FLIGHT + REFUND NOT RECEIVED
    # ========================================================

    if (
        "cancelled flight" in issue
        and "refund not received" in issue
    ):
        return CasePlan(
            summary=(
                "Prepare and pursue the passenger's applicable "
                "refund request with the airline."
            ),
            steps=[
                "Verify the flight cancellation and supporting evidence.",
                "Verify the passenger's refund eligibility.",
                "Prepare a refund request using the case details.",
                "Attach the supporting evidence.",
                "Contact the airline and submit the applicable refund request.",
                "Track the airline's response.",
                "Follow up if the airline does not respond or the refund is not received.",
            ],
            approval_required=True,
        )

    # ========================================================
    # GENERIC REFUND
    # ========================================================

    if "refund" in issue or "refund" in action:
        return CasePlan(
            summary=(
                "Verify refund eligibility and prepare the "
                "appropriate refund action."
            ),
            steps=[
                "Review the available refund evidence.",
                "Verify the applicable refund eligibility and policy.",
                "Prepare the appropriate refund request or next action.",
                "Attach the supporting evidence.",
                "Submit the action to the relevant organization.",
                "Track the response.",
                "Follow up if required.",
            ],
            approval_required=True,
        )

    # ========================================================
    # CANCELLATION
    # ========================================================

    if "cancellation" in issue or "cancelled" in issue:
        return CasePlan(
            summary=(
                "Review the cancellation circumstances and "
                "prepare the appropriate remedy."
            ),
            steps=[
                "Review the cancellation evidence.",
                "Verify the applicable policy or passenger rights.",
                "Determine the appropriate remedy.",
                "Prepare the required action.",
                "Submit the action to the relevant organization.",
                "Track the response.",
            ],
            approval_required=True,
        )

    # ========================================================
    # PAYMENT / BILLING
    # ========================================================

    if (
        "payment" in issue
        or "billing" in issue
        or "charge" in issue
    ):
        return CasePlan(
            summary=(
                "Review the payment issue and prepare the "
                "appropriate resolution."
            ),
            steps=[
                "Review the transaction evidence.",
                "Verify the charge and payment details.",
                "Determine the appropriate resolution.",
                "Prepare the required action.",
                "Submit the action to the relevant organization.",
                "Track the response.",
            ],
            approval_required=True,
        )

    # ========================================================
    # DELIVERY / ORDER
    # ========================================================

    if (
        "delivery" in issue
        or "order" in issue
    ):
        return CasePlan(
            summary=(
                "Review the delivery or order issue and "
                "prepare the appropriate resolution."
            ),
            steps=[
                "Review the order and delivery evidence.",
                "Verify the delivery status.",
                "Determine the appropriate resolution.",
                "Prepare the required action.",
                "Contact the relevant organization.",
                "Track the response.",
            ],
            approval_required=True,
        )

    # ========================================================
    # GENERIC HUMAN REVIEW
    # ========================================================

    return CasePlan(
        summary=(
            "Review the case and determine the appropriate "
            "next action."
        ),
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

    case.status = (
        CaseStatus.ACTION_READY
        if not plan.approval_required
        else CaseStatus.AWAITING_APPROVAL
    )

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
