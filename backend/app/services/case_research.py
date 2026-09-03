from dataclasses import dataclass
import os
import re
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


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _is_generic(value: str | None) -> bool:
    if not value:
        return True

    normalized = value.strip().lower()

    return normalized in {
        "abc",
        "test",
        "example",
        "unknown",
        "n/a",
        "na",
        "null",
        "none",
        "airways",
        "airline",
        "airlines",
        "air",
    }



def _build_queries(case: CaseModel) -> List[str]:
    queries: List[str] = []

    # Domain detection using case fields and supporting facts
    text_parts = []
    if case.title:
        text_parts.append(case.title)
    if case.description:
        text_parts.append(case.description)
    if case.requested_resolution:
        text_parts.append(case.requested_resolution)
    if case.supporting_facts:
        text_parts.append(case.supporting_facts)

    text_blob = " ".join(text_parts).lower()

    def detect_domain() -> str | None:
        if any(k in text_blob for k in ("insurance", "claim", "policy", "claimant", "policy number", "claim number")):
            return "insurance"
        if any(k in text_blob for k in ("flight", "airline", "passenger", "booking", "cancellation")):
            return "flight"
        if any(k in text_blob for k in ("bank", "transaction", "charge", "dispute", "account")):
            return "bank"
        if any(k in text_blob for k in ("rental", "lease", "deposit", "landlord", "tenancy")):
            return "rental"
        return None

    domain = detect_domain()

    org = case.airline or case.organization

    # Build domain-specific queries
    if domain == "insurance":
        if org and not _is_generic(org):
            queries.append(f'"{org}" insurance claim denial policy')
            queries.append(f'"{org}" claim appeal process')

        queries.extend([
            "insurance claim denial appeals guidance",
            "insurance policy denial reasons consumer protection",
            "how to appeal an insurance claim denial",
            "insurance regulator claim denial guidance site:gov",
        ])

        qbase = " ".join([p for p in (case.title, case.description, case.requested_resolution) if p])
        if qbase:
            queries.append(f"{qbase} insurance claim denial")

    elif domain == "bank":
        queries.extend([
            "bank dispute chargeback process",
            "consumer protection bank dispute",
            "how to dispute a bank transaction",
        ])

        qbase = " ".join([p for p in (case.title, case.description, case.requested_resolution) if p])
        if qbase:
            queries.append(f"{qbase} bank dispute")

    elif domain == "rental":
        queries.extend([
            "tenant deposit dispute guidance",
            "rental tenancy deposit laws",
        ])

    else:
        # Default to flight-oriented queries only when flight signals exist
        if org and not _is_generic(org):
            queries.extend([
                f'"{org}" cancelled flight refund policy',
                f'"{org}" flight cancellation refund',
                f'"{org}" passenger refund rights',
            ])

        # government/regulator fallbacks for consumer rights
        queries.extend([
            "consumer protection claim guidance site:gov",
            "consumer affairs claim dispute guidance",
        ])

        qbase = " ".join([p for p in (case.title, case.description, case.requested_resolution) if p])
        if qbase:
            queries.extend([
                f"{qbase} policy guidance",
                f"{qbase} consumer rights",
            ])

    # ---------------------------------------------------------
    # Deduplicate while preserving order
    # ---------------------------------------------------------
    seen = set()
    output = []

    for query in queries:
        query = query.strip()

        if not query:
            continue

        normalized = query.lower()

        if normalized in seen:
            continue

        seen.add(normalized)
        output.append(query)

    return output[:12]


def _authority_score(
    result: ResearchResult,
    case: CaseModel,
) -> int:
    """
    Rank research sources by authority and relevance.

    Priority:
        1. Government / regulators
        2. Official organization / airline
        3. Aviation / consumer authorities
        4. Reputable secondary sources
        5. Generic/community sources

    This is a ranking heuristic, NOT a legal determination.
    """

    score = 0

    link = (result.url or "").lower()
    source = (result.source or "").lower()
    title = (result.title or "").lower()
    summary = (result.summary or "").lower()

    searchable = " ".join(
        [
            link,
            source,
            title,
            summary,
        ]
    )

    airline = case.airline or case.organization

    airline_normalized = _normalize(airline)
    link_normalized = _normalize(link)
    source_normalized = _normalize(source)

    # ---------------------------------------------------------
    # Government / regulatory authority
    # ---------------------------------------------------------
    government_domains = (
        ".gov",
        ".gov.",
        "go.jp",
        "gov.uk",
        "europa.eu",
        "mlit.go.jp",
        "caa.go.jp",
        "transportation.gov",
        "transport.gov",
        "dot.gov",
    )

    if any(domain in link for domain in government_domains):
        score += 70

    # Government / regulator language
    government_keywords = (
        "government",
        "government agency",
        "regulator",
        "regulatory authority",
        "civil aviation authority",
        "aviation authority",
        "ministry of transport",
        "transport ministry",
        "department of transportation",
        "transportation department",
        "consumer protection",
        "consumer affairs",
        "consumer affairs agency",
        "passenger rights",
    )

    if any(keyword in searchable for keyword in government_keywords):
        score += 30

    # ---------------------------------------------------------
    # Japan-specific official authority
    # ---------------------------------------------------------
    japan_authority_keywords = (
        "mlit",
        "ministry of land infrastructure transport and tourism",
        "consumer affairs agency",
        "japan civil aviation",
        "civil aviation bureau",
        "caa japan",
    )

    if any(keyword in searchable for keyword in japan_authority_keywords):
        score += 25

    # ---------------------------------------------------------
    # Official airline / organization
    # ---------------------------------------------------------
    if airline_normalized:
        if airline_normalized in link_normalized:
            score += 50

        if airline_normalized in source_normalized:
            score += 35

        # Handle names separated by spaces / punctuation
        airline_words = [
            word
            for word in re.findall(r"[a-z0-9]+", airline.lower())
            if len(word) >= 3
        ]

        if airline_words:
            matched_words = sum(
                1
                for word in airline_words
                if word in searchable
            )

            if matched_words >= 2:
                score += 15

    # ---------------------------------------------------------
    # Aviation authoritative organizations
    # ---------------------------------------------------------
    authoritative_orgs = (
        "iata",
        "icao",
        "civil aviation",
        "aviation authority",
        "transport authority",
        "consumer protection",
        "consumer affairs",
        "regulator",
    )

    if any(keyword in searchable for keyword in authoritative_orgs):
        score += 25

    # ---------------------------------------------------------
    # Reputable secondary sources
    # ---------------------------------------------------------
    secondary_sources = (
        "reuters",
        "associated press",
        "ap news",
        "bbc",
        "bloomberg",
        "new york times",
        "nytimes",
        "guardian",
        "cnn",
        "nhk",
    )

    if any(source_name in searchable for source_name in secondary_sources):
        score += 15

    # ---------------------------------------------------------
    # URL quality
    # ---------------------------------------------------------
    if result.url:
        score += 5

    # ---------------------------------------------------------
    # Existing relevance classification
    # ---------------------------------------------------------
    relevance = (result.relevance or "").lower()

    if relevance == "high":
        score += 15
    elif relevance == "medium":
        score += 5

    # ---------------------------------------------------------
    # Case-specific identifiers
    # ---------------------------------------------------------
    identifiers = [
        case.booking_reference,
        case.flight_number,
        case.cancellation_date,
    ]

    for identifier in identifiers:
        if not identifier:
            continue

        identifier_normalized = identifier.lower().strip()

        if (
            identifier_normalized in searchable
            and len(identifier_normalized) >= 3
        ):
            score += 8

    # ---------------------------------------------------------
    # Requested outcome relevance
    # ---------------------------------------------------------
    requested_resolution = (
        case.requested_resolution or ""
    ).lower()

    if requested_resolution:
        resolution_words = [
            word
            for word in re.findall(
                r"[a-z0-9]+",
                requested_resolution,
            )
            if len(word) >= 4
        ]

        matched_resolution_words = sum(
            1
            for word in resolution_words
            if word in searchable
        )

        score += min(
            matched_resolution_words * 2,
            10,
        )

    # ---------------------------------------------------------
    # Penalize low-authority community/social sources
    # ---------------------------------------------------------
    low_authority_domains = (
        "facebook.com",
        "reddit.com",
        "quora.com",
        "pinterest.com",
        "tiktok.com",
        "instagram.com",
        "youtube.com",
    )

    if any(domain in link for domain in low_authority_domains):
        score -= 40

    low_authority_sources = (
        "facebook",
        "reddit",
        "quora",
        "forum",
        "community",
        "blogspot",
    )

    if any(source_name in source for source_name in low_authority_sources):
        score -= 20

    return score


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

    org = case.airline or case.organization
    org_lower = (org or "").lower()

    # domain detection (reuse similar heuristics as query builder)
    text_parts = []
    if case.title:
        text_parts.append(case.title)
    if case.description:
        text_parts.append(case.description)
    if case.requested_resolution:
        text_parts.append(case.requested_resolution)
    if case.supporting_facts:
        text_parts.append(case.supporting_facts)

    text_blob = " ".join(text_parts).lower()

    def _detect_domain_from_blob() -> str | None:
        if any(k in text_blob for k in ("insurance", "claim", "policy", "claimant", "policy number", "claim number")):
            return "insurance"
        if any(k in text_blob for k in ("flight", "airline", "passenger", "booking", "cancellation")):
            return "flight"
        if any(k in text_blob for k in ("bank", "transaction", "charge", "dispute", "account")):
            return "bank"
        if any(k in text_blob for k in ("rental", "lease", "deposit", "landlord", "tenancy")):
            return "rental"
        return None

    domain = _detect_domain_from_blob()

    results: List[ResearchResult] = []

    # ---------------------------------------------------------
    # Search across multiple queries.
    #
    # Important:
    # Do NOT stop after the first 5 raw results.
    # We need a larger candidate pool so authority ranking
    # can actually select the strongest sources.
    # ---------------------------------------------------------
    max_candidates = 30

    try:
        for query in queries:

            items = serpapi.search(
                query,
                api_key=api_key,
            )

            for item in items:

                title = (
                    item.get("title")
                    or item.get("headline")
                    or ""
                )

                snippet = (
                    item.get("snippet")
                    or item.get("summary")
                    or ""
                )

                source = (
                    item.get("source")
                    or item.get("engine")
                    or "web"
                )

                link = (
                    item.get("link")
                    or item.get("url")
                )

                link_lower = (link or "").lower()
                source_lower = (source or "").lower()

                # -------------------------------------------------
                # Initial relevance
                # -------------------------------------------------
                relevance = "medium"

                if any(
                    domain in link_lower
                    for domain in (
                        ".gov",
                        ".gov.",
                        "go.jp",
                        "gov.uk",
                        "europa.eu",
                    )
                ):
                    relevance = "high"

                else:
                    # Prefer strong matches only when the organization appears
                    # unambiguously in the link/title (e.g., organization domain)
                    org_words = [
                        word
                        for word in re.findall(r"[a-z0-9]+", (org or "").lower())
                        if len(word) >= 3
                    ]

                    combined_search_text = (
                        link_lower + " " + title.lower() + " " + source_lower + " " + (snippet or "").lower()
                    )

                    matched_words = sum(
                        1
                        for word in org_words
                        if word in combined_search_text
                    )

                    # If the full normalized organization equals the normalized link, it's a strong match.
                    if org and _normalize(org) and _normalize(org) == _normalize(link_lower):
                        relevance = "high"
                    elif matched_words >= 2:
                        relevance = "high"

                # -------------------------------------------------
                # Explain source role
                # -------------------------------------------------
                if any(
                    domain in link_lower
                    for domain in (
                        ".gov",
                        ".gov.",
                        "go.jp",
                        "gov.uk",
                        "europa.eu",
                    )
                ):
                    why = (
                        "This is an official government or regulatory source describing policy or guidance relevant to the issue."
                    )

                elif org and _normalize(org) and (
                    _normalize(org) == _normalize(link_lower)
                    or matched_words >= 2
                ):
                    why = (
                        "This source appears to be the organization's official policy or published guidance."
                    )

                elif any(
                    keyword in (
                        title.lower()
                        + " "
                        + source_lower
                        + " "
                        + snippet.lower()
                    )
                    for keyword in (
                        "iata",
                        "icao",
                        "authority",
                        "consumer protection",
                        "consumer affairs",
                        "regulator",
                    )
                ):
                    why = (
                        "This source provides authoritative sector or consumer-protection guidance."
                    )

                else:
                    why = (
                        "This source provides contextual information that may be relevant to the case."
                    )

                summary = (snippet or "").strip()

                if summary:
                    summary = (
                        f"{summary} — {why}"
                    )
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

                if len(results) >= max_candidates:
                    break

            if len(results) >= max_candidates:
                break

        # ---------------------------------------------------------
        # Deduplicate current research results
        # ---------------------------------------------------------
        seen_urls = set()
        seen_pairs = set()
        unique_results: List[ResearchResult] = []

        for result in results:

            if result.url:
                normalized_url = result.url.strip().lower()

                if normalized_url in seen_urls:
                    continue

                seen_urls.add(normalized_url)

            else:
                pair = (
                    (result.source or "").strip().lower(),
                    (result.title or "").strip().lower(),
                )

                if pair in seen_pairs:
                    continue

                seen_pairs.add(pair)

            unique_results.append(result)

        # ---------------------------------------------------------
        # Rank candidates
        # ---------------------------------------------------------
        scored_results = [
            (
                result,
                _authority_score(
                    result,
                    case,
                ),
            )
            for result in unique_results
        ]

        # Python's sort is stable, so equal scores retain
        # their original search order.
        scored_results.sort(
            key=lambda pair: pair[1],
            reverse=True,
        )

        # Keep only the strongest five sources.
        ranked_results = [
            result
            for result, score in scored_results[:5]
        ]

        # ---------------------------------------------------------
        # Existing persisted research
        # ---------------------------------------------------------
        existing = (
            db.query(CaseResearch)
            .filter(
                CaseResearch.case_id == case.id
            )
            .all()
        )

        existing_urls = set()
        existing_pairs = set()

        for existing_result in existing:

            if existing_result.url:
                existing_urls.add(
                    existing_result.url.strip().lower()
                )

            else:
                existing_pairs.add(
                    (
                        (
                            existing_result.source
                            or ""
                        ).strip().lower(),
                        (
                            existing_result.title
                            or ""
                        ).strip().lower(),
                    )
                )

        # ---------------------------------------------------------
        # Persist ranked results
        # ---------------------------------------------------------
        for result in ranked_results:

            if result.url:

                normalized_url = (
                    result.url.strip().lower()
                )

                if normalized_url in existing_urls:
                    continue

                existing_urls.add(normalized_url)

            else:

                pair = (
                    (
                        result.source
                        or ""
                    ).strip().lower(),
                    (
                        result.title
                        or ""
                    ).strip().lower(),
                )

                if pair in existing_pairs:
                    continue

                existing_pairs.add(pair)

            db.add(
                CaseResearch(
                    case_id=case.id,
                    source=result.source,
                    title=result.title,
                    summary=result.summary,
                    relevance=result.relevance,
                    url=result.url,
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
                "ONIT completed research and selected "
                f"{len(ranked_results)} highest-authority "
                "source(s) from the research candidate pool."
            ),
        )

        return ranked_results

    except Exception as exc:

        record_activity(
            db=db,
            case_id=case.id,
            event_type="RESEARCH_FAILED",
            message=f"Research failed: {str(exc)}",
        )

        case.status = CaseStatus.EVIDENCE_READY

        db.commit()

        raise ValueError(str(exc)) from exc