import json

from app.services.case_parser import Case as ParsedCase
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.case_persistence import persist_parsed_case
from app.services.case_analysis import analyze_case
from app.models.case import Case as CaseModel, CaseStatus


def test_evaluate_sufficient_fixture():
    with open("tests/fixtures/nutrient_response.json", encoding="utf-8") as f:
        resp = json.load(f)

    parsed = __import__(
        "app.services.case_parser",
        fromlist=["parse_case"],
    ).parse_case(resp)

    suff = evaluate_evidence_sufficiency(parsed)

    assert suff["needs_information"] is False
    assert isinstance(suff["missing_information"], list)


def test_evaluate_insufficient():
    """
    A completely empty case should be rejected, but ONIT must not
    require flight-specific fields such as booking_reference or
    passenger for every case.
    """

    parsed = ParsedCase(
        passenger=None,
        booking_reference=None,
        airline=None,
        cancellation_date=None,
        amount=None,
        supporting_facts=[],
        requested_resolution=None,
    )

    suff = evaluate_evidence_sufficiency(parsed)

    assert suff["needs_information"] is True

    fields = [
        m["field"]
        for m in suff["missing_information"]
    ]

    assert "case_details" in fields
    assert "booking_reference" not in fields
    assert "passenger" not in fields


def test_needs_information_status_and_persistence(tmp_path):
    # An empty case should remain NEEDS_INFORMATION.
    parsed = ParsedCase(
        passenger=None,
        booking_reference=None,
        airline=None,
        cancellation_date=None,
        amount=None,
        supporting_facts=[],
        requested_resolution=None,
    )

    from app.db.database import SessionLocal

    db = SessionLocal()

    case = persist_parsed_case(db, parsed)

    analyze_case(db, case)

    db.refresh(case)

    assert case.status == CaseStatus.NEEDS_INFORMATION
    assert case.missing_information is not None

    miss = json.loads(case.missing_information)

    assert miss.get("needs_information") is True
    assert isinstance(
        miss.get("missing_information"),
        list,
    )


def test_missing_information_cleared_when_provided(tmp_path):
    """
    Once meaningful case information is supplied, ONIT should no
    longer require the generic case_details field.

    This deliberately uses generic information rather than relying
    on flight-specific passenger/booking fields.
    """

    parsed = ParsedCase(
        passenger=None,
        booking_reference=None,
        airline=None,
        cancellation_date=None,
        amount=None,
        supporting_facts=[],
        requested_resolution=None,
    )

    from app.db.database import SessionLocal

    db = SessionLocal()

    case = persist_parsed_case(db, parsed)

    # Initial analysis -> insufficient.
    analyze_case(db, case)

    db.refresh(case)

    assert case.status == CaseStatus.NEEDS_INFORMATION

    # Simulate the user providing meaningful case information.
    case.description = (
        "The service I paid for was cancelled and I have "
        "not received the refund."
    )
    case.amount = "52800"

    db.commit()
    db.refresh(case)

    # Re-run analysis.
    decision = analyze_case(db, case)

    db.refresh(case)

    assert case.status != CaseStatus.NEEDS_INFORMATION
    assert decision is not None


def test_existing_flight_workflow_regression(tmp_path):
    # Existing flight fixture must continue to work.
    with open("tests/fixtures/nutrient_response.json", encoding="utf-8") as f:
        resp = json.load(f)

    parsed = __import__(
        "app.services.case_parser",
        fromlist=["parse_case"],
    ).parse_case(resp)

    from app.db.database import SessionLocal

    db = SessionLocal()

    case = persist_parsed_case(db, parsed)

    decision = analyze_case(db, case)

    db.refresh(case)

    assert case.status == CaseStatus.EVIDENCE_READY
    assert decision is not None
