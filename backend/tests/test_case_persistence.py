import json

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel
from app.services.case_parser import Case as ParsedCase
from app.services.case_persistence import persist_parsed_case


def test_persist_parsed_case():
    db = SessionLocal()

    try:
        parsed_case = ParsedCase(
            passenger="Alex Morgan",
            booking_reference="ABC123",
            airline="Example Airways",
            cancellation_date="August 1, 2026",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            supporting_facts=["Booking reference: ABC123"],
        )

        case = persist_parsed_case(db, parsed_case)

        assert case.id is not None
        assert case.passenger == "Alex Morgan"
        assert case.booking_reference == "ABC123"
        assert case.airline == "Example Airways"
        assert case.organization == "Example Airways"
        assert case.amount == "Y120,000"
        assert case.refund_received is False
        assert case.requested_resolution == "Refund the full Y120,000"

        assert json.loads(case.supporting_facts) == [
            "Booking reference: ABC123"
        ]

        stored = db.get(CaseModel, case.id)

        assert stored is not None
        assert stored.passenger == "Alex Morgan"
        assert stored.status.value == "CREATED"

    finally:
        db.close()
