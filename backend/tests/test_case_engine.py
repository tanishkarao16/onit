from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_case_persists_and_can_be_retrieved():
    response = client.post(
        "/cases",
        json={
            "title": "Flight cancellation refund",
            "description": "Passenger is requesting a full refund after cancellation.",
            "organization": "Example Airways",
            "amount": "120000",
            "currency": "JPY",
        },
    )

    assert response.status_code == 200

    created = response.json()

    assert created["status"] == "ok"
    assert created["case"]["title"] == "Flight cancellation refund"
    assert created["case"]["status"] == "CREATED"

    case_id = created["case"]["id"]

    get_response = client.get(f"/cases/{case_id}")

    assert get_response.status_code == 200

    retrieved = get_response.json()

    assert retrieved["status"] == "ok"
    assert retrieved["case"]["id"] == case_id
    assert retrieved["case"]["title"] == "Flight cancellation refund"
    assert retrieved["case"]["description"] == (
        "Passenger is requesting a full refund after cancellation."
    )
    assert retrieved["case"]["organization"] == "Example Airways"
    assert retrieved["case"]["amount"] == "120000"
    assert retrieved["case"]["currency"] == "JPY"
    assert retrieved["case"]["status"] == "CREATED"
