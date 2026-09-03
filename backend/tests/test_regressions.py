import json

from app.services.case_parser import parse_case, Case as ParsedCase
from app.services.case_decision import decide_case
from app.services import case_research
from app.services.case_persistence import persist_parsed_case
from app.db.database import SessionLocal
from app.services import evidence_to_decision


def _make_response_with_text(text: str) -> dict:
    return {
        "elements": [
            {"role": "Text", "text": text, "confidence": 0.9}
        ]
    }


def test_yen_120000_parses_correctly():
    resp = _make_response_with_text("Amount paid: ¥120,000")
    parsed = parse_case(resp)

    assert parsed.amount == "¥120,000"
    assert parsed.amount_value == "120000"
    assert parsed.amount_currency == "JPY"


def test_yen_52800_still_parses():
    resp = _make_response_with_text("Amount paid: ¥52,800")
    parsed = parse_case(resp)

    assert parsed.amount == "¥52,800"
    assert parsed.amount_value == "52800"
    assert parsed.amount_currency == "JPY"


def test_insurance_decision_not_classified_as_flight():
    # Create a parsed case that clearly represents an insurance denial
    parsed = ParsedCase(
        passenger=None,
        booking_reference=None,
        airline=None,
        cancellation_date=None,
        flight_number=None,
        amount="¥10,000",
        amount_value="10000",
        amount_currency="JPY",
        refund_received=None,
        requested_resolution="Reconsider claim",
        supporting_facts=["Claim denied due to coverage exclusion"],
        facts={"claim_number": "CN123", "policy_number": "PN456"},
    )

    decision = decide_case(parsed)

    # Should be insurance-related, not a flight/refund decision
    assert "insurance" in decision.issue.lower() or "claim" in decision.issue.lower()
    assert "flight" not in decision.issue.lower()
    assert "refund" not in decision.issue.lower()


def test_insurance_query_generation_is_insurance_focused():
    class Dummy:
        pass

    c = Dummy()
    c.title = "Insurance claim denied"
    c.description = "Claim denied for policy ABC"
    c.requested_resolution = "Reconsideration"
    c.supporting_facts = "Claim number: CN123"
    c.airline = None
    c.organization = None
    # ensure attributes expected by authority scorer exist
    c.booking_reference = None
    c.flight_number = None
    c.cancellation_date = None

    queries = case_research._build_queries(c)

    # At least one query should reference insurance/claim concepts
    assert any(
        ("insurance" in q.lower() or "claim" in q.lower() or "denial" in q.lower())
        for q in queries
    )

    # Early queries should not default to airline/passenger refund concepts
    assert not any("airline" in q.lower() or "passenger" in q.lower() for q in queries[:5])


def test_irrelevant_sources_not_high_for_insurance():
    # Build a dummy case representing insurance
    class Dummy:
        pass

    c = Dummy()
    c.title = "Insurance claim denied"
    c.description = "Claim denied for policy ABC"
    c.requested_resolution = "Reconsideration"
    c.supporting_facts = "Claim number: CN123"
    c.airline = None
    c.organization = None
    # ensure attributes expected by authority scorer exist
    c.booking_reference = None
    c.flight_number = None
    c.cancellation_date = None

    # Relevant government insurance regulator source
    relevant = case_research.ResearchResult(
        source="Consumer Affairs",
        title="Insurance claim denial guidance",
        summary="Guidance on appealing insurance denials",
        relevance="high",
        url="https://consumer.example.gov/insurance/denial",
    )

    # Irrelevant .gov (SEC filing) and unrelated medical article
    irrelevant1 = case_research.ResearchResult(
        source="SEC",
        title="Company filing",
        summary="SEC filing content",
        relevance="medium",
        url="https://www.sec.gov/filing",
    )

    irrelevant2 = case_research.ResearchResult(
        source="Medical Journal",
        title="Health study",
        summary="Unrelated medical content",
        relevance="medium",
        url="https://medical.example.com/study",
    )

    score_rel = case_research._authority_score(relevant, c)
    score_irr1 = case_research._authority_score(irrelevant1, c)
    score_irr2 = case_research._authority_score(irrelevant2, c)

    # Relevant source should score higher than clearly irrelevant ones
    assert score_rel > score_irr1
    assert score_rel > score_irr2


def test_confidence_and_strength_not_strong_from_irrelevant_pool():
    # Create 5 irrelevant CaseResearch-like objects
    class Item:
        def __init__(self, relevance: str, url: str):
            self.relevance = relevance
            self.url = url

    items = [Item("medium", "https://example.com/article") for _ in range(5)]

    strength = evidence_to_decision._compute_evidence_strength(items)
    confidence = evidence_to_decision._compute_confidence(items)

    # Should not be strong solely because 5 irrelevant/medium items exist
    assert strength != "strong"
    assert confidence < 95


def test_arbitrary_facts_survive_parsing_and_persistence():
    resp = _make_response_with_text("Claim number: CN999\nPolicy number: PN888\nAmount: ¥75,000")
    parsed = parse_case(resp)

    # Ensure facts mapping contains normalized keys
    assert parsed.facts is not None
    assert parsed.facts.get("claim_number") == "CN999"
    assert parsed.facts.get("policy_number") == "PN888"

    # Persist and verify supporting_facts stored
    db = SessionLocal()
    try:
        case = persist_parsed_case(db, parsed)
        assert case.supporting_facts is not None
        loaded = json.loads(case.supporting_facts)
        assert isinstance(loaded, list)
    finally:
        db.delete(case)
        db.commit()
