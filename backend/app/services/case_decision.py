from dataclasses import dataclass

from app.services.case_parser import Case


@dataclass
class CaseDecision:
    issue: str
    recommended_action: str
    priority: str
    reason: str


def decide_case(case: Case) -> CaseDecision:
    """
    Determine the next action ONIT should take based on the structured case.
    This first version is deterministic so it is cheap, testable, and reliable.
    """

    if (
        case.amount
        and case.refund_received is False
        and case.requested_resolution
    ):
        return CaseDecision(
            issue="Cancelled flight with refund not received",
            recommended_action="Request the full refund from the airline",
            priority="high",
            reason=(
                f"The booking was cancelled, no refund has been received, "
                f"and the requested resolution is: "
                f"{case.requested_resolution}"
            ),
        )

    return CaseDecision(
        issue="Case requires review",
        recommended_action="Review the case and determine the appropriate next action",
        priority="medium",
        reason="The available case information does not match a known automated workflow.",
    )
