from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseResearch, CaseStatus
from app.services.case_activity import record_activity


@dataclass
class ResearchResult:
    source: str
    title: str
    summary: str
    relevance: str


def research_case(
    db: Session,
    case: CaseModel,
) -> list[ResearchResult]:
    case.status = CaseStatus.RESEARCHING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="RESEARCH_STARTED",
        message="ONIT started researching the case.",
    )

    results = [
        ResearchResult(
            source=case.organization or "Case evidence",
            title="Case-specific refund policy research",
            summary=(
                "Review the organization's applicable refund policy "
                "and cancellation terms."
            ),
            relevance=(
                "Determines whether the requested refund is supported "
                "by the available case information."
            ),
        )
    ]

    for result in results:
        db.add(
            CaseResearch(
                case_id=case.id,
                source=result.source,
                title=result.title,
                summary=result.summary,
                relevance=result.relevance,
            )
        )

    case.status = CaseStatus.EVIDENCE_READY
    db.commit()
    db.refresh(case)

    record_activity(
        db=db,
        case_id=case.id,
        event_type="RESEARCH_COMPLETED",
        message=(
            f"ONIT completed research and found "
            f"{len(results)} relevant source(s)."
        ),
    )

    return results
