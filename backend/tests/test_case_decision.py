from app.services.case_decision import decide_case
from app.services.case_parser import Case


def test_decide_refund_case():
    case = Case(
        passenger="Alex Morgan",
        booking_reference="ABC123",
        airline="Example Airways",
        cancellation_date="August 1, 2026",
        amount="Y120,000",
        refund_received=False,
        requested_resolution="Refund the full Y120,000",
        supporting_facts=[
            "Booking reference: ABC123",
            "Amount paid: Y120,000",
            "Cancellation: Confirmed by airline",
            "Refund received: No",
        ],
    )

    decision = decide_case(case)

    # ONIT identifies the specific case type.
    assert decision.issue == (
        "Cancelled flight with refund not received"
    )

    # ONIT's workflow is action-oriented:
    # verify eligibility -> contact the third party ->
    # follow up until a response is received.
    assert decision.recommended_action == (
        "Verify the passenger's refund eligibility, "
        "contact the airline to request the applicable "
        "refund, and follow up until a response is received."
    )

    assert decision.priority == "high"

    # The reason should explain the decision
    # using the actual case facts.
    assert "cancelled" in decision.reason.lower()
    assert "refund" in decision.reason.lower()
    assert "Y120,000" in decision.reason