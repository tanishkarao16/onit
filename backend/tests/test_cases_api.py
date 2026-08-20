from fastapi.testclient import TestClient

from app.main import app
from app.api import cases


client = TestClient(app)


def test_parse_case_endpoint(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {"role": "Text", "text": "Passenger: Alex Morgan\nBooking reference: ABC123"},
                {"role": "Text", "text": "Airline: Example Airways"},
                {"role": "Text", "text": "Flight cancellation date: August 1, 2026"},
                {"role": "Text", "text": "Amount paid: Y120,000"},
                {"role": "Text", "text": "Refund received: No"},
                {
                    "role": "Text",
                    "text": "Requested resolution:\nRefund the full Y120,000",
                },
                {"role": "ListItem", "text": "- Booking reference: ABC123"},
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        cases,
        "parse_document",
        fake_parse_document,
    )

    with open("tests/fixtures/refund_case.pdf", "rb") as document:
        response = client.post(
            "/cases/parse",
            files={
                "file": (
                    "refund_case.pdf",
                    document,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["case"]["passenger"] == "Alex Morgan"
    assert data["case"]["booking_reference"] == "ABC123"
    assert data["case"]["airline"] == "Example Airways"
    assert data["case"]["amount"] == "Y120,000"
    assert data["case"]["refund_received"] is False
