from dataclasses import dataclass
import os
from typing import List

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseResearch, CaseStatus
from app.services.case_activity import record_activity
from app.integrations import serpapi


@dataclass
class ResearchResult:
    source: str
    title: str
    summary: str
    relevance: str
    url: str | None = None


def _build_queries(case: CaseModel) -> List[str]:
    parts: List[str] = []
    # Build queries using the most relevant case fields.
    def is_generic(name: str) -> bool:
        if not name:
            return True
        n = name.strip().lower()
        generic = {"abc", "test", "example", "unknown", "n/a", "na", "null"}
        return n in generic

    tokens: List[str] = []

    if case.title:
        tokens.append(case.title)
    if case.description:
        tokens.append(case.description)
    if case.airline and not is_generic(case.airline):
        tokens.append(case.airline)
    if case.organization and not is_generic(case.organization) and case.organization != case.airline:
        tokens.append(case.organization)
    if case.requested_resolution:
        tokens.append(case.requested_resolution)
    if case.cancellation_date:
        tokens.append(case.cancellation_date)
    if case.booking_reference:
        tokens.append(case.booking_reference)
    if case.supporting_facts:
        tokens.append(case.supporting_facts)

    queries: List[str] = []

    # Prefer airline-focused authoritative queries
    airline = case.airline or case.organization
    airline_lower = (airline or "").lower()
    if airline and not is_generic(airline):
        queries.append(f"{airline} cancelled flight refund policy")
        queries.append(f"{airline} refund policy passenger rights")
        queries.append(f"{airline} passenger refund rights site:gov")

    # Consumer protection / aviation authority queries
    if case.booking_reference or case.requested_resolution or case.cancellation_date:
        qbase = " ".join(t for t in [case.title, case.description, case.requested_resolution] if t)
        if qbase:
            queries.append(f"{qbase} refund policy")
            queries.append(f"{qbase} passenger rights site:gov")

    # Generic fallback using tokens
    token_base = " ".join([t for t in tokens if t])
    if token_base:
        queries.append(f"{token_base} refund policy")
        queries.append(f"{token_base} passenger rights")

    # final fallback
    if not queries:
        queries.append("flight cancellation refund policy")

    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for q in queries:
        qn = q.strip()
        if qn and qn not in seen:
            seen.add(qn)
            out.append(qn)

    # Limit to reasonable count
    return out[:10]


def research_case(
    db: Session,
    case: CaseModel,
) -> list[ResearchResult]:
    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        raise ValueError("Missing SERPAPI_API_KEY")

    case.status = CaseStatus.RESEARCHING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="RESEARCH_STARTED",
        message="ONIT started researching the case.",
    )

    queries = _build_queries(case)
    airline = case.airline or case.organization
    airline_lower = (airline or "").lower()

    results: List[ResearchResult] = []

    try:
        for q in queries:
            items = serpapi.search(q, api_key=api_key)

            for item in items:
                title = item.get("title") or item.get("headline") or ""
                snippet = item.get("snippet") or item.get("summary") or ""
                source = item.get("source") or item.get("engine") or "web"
                link = item.get("link") or item.get("url")

                # Heuristic relevance
                relevance = "medium"
                lnk = (link or "").lower()
                if lnk and any(k in lnk for k in [".gov", ".gov.", "gov."]):
                    relevance = "high"
                elif airline_lower and airline_lower in lnk:
                    relevance = "high"

                # Explain why the source matters
                why = ""
                if "gov" in (source or "") or (link and ".gov" in link):
                    why = "This is an official government or regulator source describing passenger rights or guidance."
                elif (airline_lower and airline_lower in (source or "")) or (link and airline_lower and airline_lower in (link or "")):
                    why = "This source appears to be the airline's official policy or published guidance."
                else:
                    why = "This source provides news or guidance relevant to refunds and passenger rights."

                summary = (snippet or "").strip()
                if summary:
                    summary = f"{summary} — {why}"
                else:
                    summary = why

                results.append(
                    ResearchResult(
                        source=source,
                        title=title,
                        summary=summary,
                        relevance=relevance,
                        url=link,
                    )
                )

            # stop early if we've gathered a reasonable number
            if len(results) >= 5:
                break

        # deduplicate results list itself (same URL or same source+title across queries)
        seen_urls_run = set()
        seen_pairs_run = set()
        unique_results = []
        for r in results:
            if r.url:
                if r.url in seen_urls_run:
                    continue
                seen_urls_run.add(r.url)
            else:
                pair = (r.source or "", r.title or "")
                if pair in seen_pairs_run:
                    continue
                seen_pairs_run.add(pair)
            unique_results.append(r)

        # persist with idempotency: avoid inserting duplicates for same case
        # gather existing persisted keys (url preferred, fallback to source+title)
        existing = (
            db.query(CaseResearch)
            .filter(CaseResearch.case_id == case.id)
            .all()
        )

        existing_urls = set()
        existing_pairs = set()
        for e in existing:
            if e.url:
                existing_urls.add(e.url)
            else:
                existing_pairs.add((e.source or "", e.title or ""))

        for idx, r in enumerate(unique_results):
            # try to capture URL from the original serpapi result stored in local loop
            # The serpapi.search returns dicts and we persisted link earlier in local items
            # We didn't store link on ResearchResult to keep backward compatibility, so read from serpapi again is not ideal.
            # Instead, attempt to read link from items by re-running a quick search for the title — but that's costly.
            # To preserve simplicity, if the original item had 'link' it was assigned to ResearchResult via local scope: modify search call to include link by adding attribute to ResearchResult.
            # dedupe: prefer URL when present
            if r.url:
                if r.url in existing_urls:
                    continue
                existing_urls.add(r.url)
            else:
                pair = (r.source or "", r.title or "")
                if pair in existing_pairs:
                    continue
                existing_pairs.add(pair)

            db.add(
                CaseResearch(
                    case_id=case.id,
                    source=r.source,
                    title=r.title,
                    summary=r.summary,
                    relevance=r.relevance,
                    url=(r.url),
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
                f"ONIT completed research and found {len(unique_results)} relevant source(s)."
            ),
        )

        return unique_results

    except Exception as exc:
        # record failure and surface a ValueError for API layer handling
        record_activity(
            db=db,
            case_id=case.id,
            event_type="RESEARCH_FAILED",
            message=f"Research failed: {str(exc)}",
        )

        # revert to evidence ready for safety
        case.status = CaseStatus.EVIDENCE_READY
        db.commit()

        raise ValueError(str(exc)) from exc
