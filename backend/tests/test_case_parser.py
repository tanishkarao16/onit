import json

from app.services.case_parser import parse_case


def load_fixture():
    with open("tests/fixtures/nutrient_response.json", encoding="utf-8") as f:
        return json.load(f)


def test_parse_refund_case():
    response = load_fixture()

    case = parse_case(response)

    assert case.passenger == "Alex Morgan"
    assert case.booking_reference == "ABC123"
    assert case.airline == "Example Airways"
    assert case.cancellation_date == "August 1, 2026"
    assert case.amount == "Y120,000"
    assert case.refund_received is False

    assert any(
        "ABC123" in fact
        for fact in case.supporting_facts
    )


def test_parse_case_handles_missing_fields():
    response = {
        "output": {
            "elements": []
        }
    }

    case = parse_case(response)

    assert case.passenger is None
    assert case.booking_reference is None
    assert case.airline is None
    assert case.cancellation_date is None
    assert case.amount is None
    assert case.refund_received is None
    assert case.requested_resolution is None
    assert case.supporting_facts == []


def test_refund_received_yes():
    response = load_fixture()

    for element in response["output"]["elements"]:
        if element.get("role") == "ListItem" and "Refund received:" in element.get("text", ""):
            element["text"] = "Refund received: Yes"

    case = parse_case(response)

    assert case.refund_received is True


def test_parse_tanishka_sample():
    with open("tests/fixtures/nutrient_response_tanishka.json", encoding="utf-8") as f:
        response = json.load(f)

    case = parse_case(response)

    assert case.passenger == "Tanishka Rao"
    assert case.booking_reference == "SKR8F2"
    assert case.airline == "Sakura Airways"
    assert case.flight_number == "SK123"
    assert case.cancellation_date == "September 1, 2026"
    assert case.amount is not None and "¥52,800" in case.amount
    assert case.refund_received is False
    assert case.requested_resolution is not None and "full refund" in case.requested_resolution.lower()
    assert isinstance(case.supporting_facts, list)
    assert len(case.supporting_facts) >= 4

