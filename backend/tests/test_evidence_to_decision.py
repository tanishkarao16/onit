import json

from app.db.database import SessionLocal
from app.models.case import (
    Case as CaseModel,
    CaseResearch,
    CaseActivity,
    CaseStatus,
)
from app.services.evidence_to_decision import synthesize_evidence_and_plan


def test_synthesize_with_authoritative_research(monkeypatch):
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a full refund.",
            passenger="Alex Morgan",
            booking_reference="ABC123",
            organization="Example Airways",
            airline="Example Airways",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        # authoritative research (gov link)
        r = CaseResearch(
            case_id=case.id,
            source="gov.example",
            title="Passenger rights for refunds",
            summary="Official guidance",
            relevance="high",
            url="https://gov.example/refunds",
        )

        db.add(r)
        db.commit()

        res = synthesize_evidence_and_plan(db=db, case=case)

        assert res["issue"]
        assert res["plan_summary"]
        assert isinstance(res["plan_steps"], list)
        # authoritative evidence should allow auto-action
        assert res["approval_required"] is True
        assert res["status"] == CaseStatus.AWAITING_APPROVAL

    finally:
        db.close()


def test_synthesize_insufficient_evidence():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Small question",
            description="No research available.",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            synthesize_evidence_and_plan(db=db, case=case)
            assert False, "Expected ValueError for insufficient evidence"
        except ValueError:
            activities = (
                db.query(CaseActivity)
                .filter(CaseActivity.case_id == case.id)
                .all()
            )
            assert any(a.event_type == "EVIDENCE_INSUFFICIENT" for a in activities)

    finally:
        db.close()


def test_synthesize_with_generic_organization_uses_evidence():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Question",
            description="Testing generic org",
            organization="abc",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        # low-quality research
        r = CaseResearch(
            case_id=case.id,
            source="example.com",
            title="Some blog",
            summary="Not authoritative",
            relevance="low",
            url="https://example.com/article",
        )

        db.add(r)
        db.commit()

        res = synthesize_evidence_and_plan(db=db, case=case)

        # Should produce a plan but require approval
        assert res["plan_summary"]
        assert res["approval_required"] is True
        assert res["status"] == CaseStatus.AWAITING_APPROVAL

    finally:
        db.close()


def test_synthesize_reports_confidence_and_evidence_strength():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a full refund.",
            passenger="Alex Morgan",
            booking_reference="ABC123",
            organization="Example Airways",
            airline="Example Airways",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        db.add_all([
            CaseResearch(
                case_id=case.id,
                source="gov.example",
                title="Passenger rights for refunds",
                summary="Official guidance",
                relevance="high",
                url="https://gov.example/refunds",
            ),
            CaseResearch(
                case_id=case.id,
                source="official airline policy",
                title="Airline refund policy",
                summary="Airline policy",
                relevance="high",
                url="https://airline.example/refund-policy",
            ),
            CaseResearch(
                case_id=case.id,
                source="news.example",
                title="Recent refund trends",
                summary="News article",
                relevance="medium",
                url="https://news.example/refunds",
            ),
        ])
        db.commit()

        res = synthesize_evidence_and_plan(db=db, case=case)

        assert res["evidence_strength"] == "strong"
        assert res["confidence"] >= 70
        assert res["stance"]["supporting"] >= 1
        assert res["stance"]["total"] == 3

    finally:
        db.close()


def test_synthesize_reports_insufficient_evidence_strength():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Question",
            description="Testing generic org",
            organization="abc",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        r = CaseResearch(
            case_id=case.id,
            source="example.com",
            title="Some blog",
            summary="Not authoritative",
            relevance="low",
            url="https://example.com/article",
        )

        db.add(r)
        db.commit()

        res = synthesize_evidence_and_plan(db=db, case=case)

        assert res["evidence_strength"] == "insufficient"
        assert res["confidence"] < 70
        assert res["stance"]["total"] == 1

    finally:
        db.close()
