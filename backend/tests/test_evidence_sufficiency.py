import json

from sqlalchemy.orm import Session

from app.services.case_parser import Case as ParsedCase
from app.services.evidence_sufficiency import evaluate_evidence_sufficiency
from app.services.case_persistence import persist_parsed_case
from app.services.case_analysis import analyze_case
from app.models.case import Case as CaseModel, CaseStatus


def test_evaluate_sufficient_fixture():
    with open("tests/fixtures/nutrient_response.json", encoding="utf-8") as f:
        resp = json.load(f)

    parsed = __import__("app.services.case_parser", fromlist=["parse_case"]).parse_case(resp)

    suff = evaluate_evidence_sufficiency(parsed)

    assert suff["needs_information"] is False
    assert isinstance(suff["missing_information"], list)


def test_evaluate_insufficient():
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
    fields = [m["field"] for m in suff["missing_information"]]
    assert "booking_reference" in fields
    assert "passenger" in fields
    assert "requested_resolution" in fields


def test_needs_information_status_and_persistence(tmp_path):
    # Create a parsed case with missing identity
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

    # persist into DB
    case = persist_parsed_case(db, parsed)

    # Analyze; should set NEEDS_INFORMATION
    decision = analyze_case(db, case)

    db.refresh(case)

    assert case.status == CaseStatus.NEEDS_INFORMATION
    assert case.missing_information is not None

    miss = json.loads(case.missing_information)
    assert miss.get("needs_information") is True
    assert isinstance(miss.get("missing_information"), list)


def test_missing_information_cleared_when_provided(tmp_path):
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

    # Analyze -> needs info
    analyze_case(db, case)

    # Now simulate user providing booking_reference via new evidence merge
    case.booking_reference = "BR123"
    case.passenger = "Test Person"
    db.commit()
    db.refresh(case)

    # Re-run analyze; should now be EVIDENCE_READY or proceed
    decision = analyze_case(db, case)

    db.refresh(case)

    assert case.status != CaseStatus.NEEDS_INFORMATION


def test_existing_flight_workflow_regression(tmp_path):
    # Load full fixture and persist
    with open("tests/fixtures/nutrient_response.json", encoding="utf-8") as f:
        resp = json.load(f)

    parsed = __import__("app.services.case_parser", fromlist=["parse_case"]).parse_case(resp)

    from app.db.database import SessionLocal

    db = SessionLocal()

    case = persist_parsed_case(db, parsed)

    # Analyze should produce a decision and EVIDENCE_READY
    decision = analyze_case(db, case)

    db.refresh(case)

    assert case.status == CaseStatus.EVIDENCE_READY
    assert decision is not None
