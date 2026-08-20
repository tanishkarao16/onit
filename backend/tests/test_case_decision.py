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

    assert decision.issue == "Cancelled flight with refund not received"
    assert decision.recommended_action == "Request the full refund from the airline"
    assert decision.priority == "high"
    assert "Y120,000" in decision.reason
