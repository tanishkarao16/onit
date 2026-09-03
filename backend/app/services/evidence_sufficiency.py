import json
import re
from typing import Any


_FIELD_HELP = {
    "organization": {
        "question": "Which organization or provider is involved?",
        "reason": "Helps identify the relevant organization for the case.",
    },
    "amount": {
        "question": "What amount is involved?",
        "reason": "Needed when the case concerns money or a financial claim.",
    },
    "requested_resolution": {
        "question": "What outcome are you seeking?",
        "reason": "Helps ONIT understand the desired resolution.",
    },
    "claim_number": {
        "question": "What is the claim number?",
        "reason": "Helps identify the relevant claim.",
    },
    "policy_number": {
        "question": "What is the policy number?",
        "reason": "Helps identify the relevant policy.",
    },
}


def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            _text(item)
            for item in value
            if item is not None
        )

    return str(value).strip()


def _has_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, bool):
        return True

    if isinstance(value, (list, tuple, set)):
        return any(_has_value(item) for item in value)

    return bool(str(value).strip())


def _case_text(parsed_case: Any) -> str:
    parts = []

    for field_name in (
        "description",
        "title",
        "passenger",
        "claimant",
        "organization",
        "airline",
        "booking_reference",
        "claim_number",
        "policy_number",
        "flight_number",
        "cancellation_date",
        "incident_date",
        "amount",
        "amount_value",
        "amount_currency",
        "refund_received",
        "claim_status",
        "requested_resolution",
        "reason_for_cancellation",
        "reason_for_denial",
        "status",
        "issue",
    ):
        value = getattr(parsed_case, field_name, None)

        if _has_value(value):
            parts.append(_text(value))

    facts = getattr(parsed_case, "supporting_facts", None)

    if facts:
        parts.append(_text(facts))

    return " ".join(parts).strip().lower()


def _looks_like_financial_case(text: str) -> bool:
    return any(
        keyword in text
        for keyword in (
            "refund",
            "reimbursement",
            "reimburse",
            "claim amount",
            "payment",
            "charge",
            "transaction",
            "money",
            "cost",
            "premium",
            "deposit",
            "compensation",
            "invoice",
            "billing",
            "fee",
        )
    )


def _looks_like_insurance_case(text: str) -> bool:
    return any(
        keyword in text
        for keyword in (
            "insurance",
            "insurer",
            "insurance claim",
            "policy",
            "claimant",
            "claim number",
            "coverage",
            "covered",
            "denial",
            "denied claim",
        )
    )


def _looks_like_flight_case(text: str) -> bool:
    return any(
        keyword in text
        for keyword in (
            "flight",
            "airline",
            "airways",
            "passenger",
            "booking reference",
            "flight number",
            "boarding",
            "airport",
            "cancellation",
            "cancelled flight",
            "canceled flight",
        )
    )


def _looks_like_meaningful_problem(text: str) -> bool:
    """
    Determine whether the case contains a meaningful problem,
    request, event, or situation that ONIT can reason about.

    This is intentionally domain-neutral.
    """

    if not text:
        return False

    normalized = re.sub(r"\s+", " ", text).strip()

    if len(normalized) < 12:
        return False

    vague_only = {
        "missing identity",
        "identity missing",
        "need help",
        "help",
        "problem",
        "issue",
        "something happened",
        "not sure",
        "unknown",
    }

    if normalized in vague_only:
        return False

    problem_signals = (
        "cancel",
        "denied",
        "reject",
        "refus",
        "disput",
        "complaint",
        "not received",
        "missing",
        "charged",
        "failed",
        "wrong",
        "damaged",
        "broken",
        "delay",
        "delayed",
        "lost",
        "stolen",
        "claim",
        "request",
        "need",
        "want",
        "issue",
        "problem",
        "cannot",
        "can't",
        "unable",
        "error",
        "refund",
        "payment",
        "insurance",
        "service",
        "contract",
        "purchase",
        "delivery",
        "account",
    )

    if any(signal in normalized for signal in problem_signals):
        return True

    return len(normalized.split()) >= 8


def evaluate_evidence_sufficiency(parsed_case: Any) -> dict:
    """
    Determine whether ONIT has enough information to continue.

    No domain-specific field is universally required.

    Generic cases can proceed when they contain a meaningful
    problem or request. Financial cases require an amount when
    the financial amount is necessary to reason about the case.

    Flight and insurance detection is informational only.
    """

    missing: list[dict[str, str]] = []

    text = _case_text(parsed_case)

    # --------------------------------------------------------
    # 1. Generic minimum
    # --------------------------------------------------------

    if not _looks_like_meaningful_problem(text):
        missing.append(
            {
                "field": "case_details",
                "question": "Please provide more details about the problem.",
                "reason": (
                    "ONIT needs enough information to understand "
                    "what happened and determine the next step."
                ),
            }
        )

    # --------------------------------------------------------
    # 2. Financial cases
    # --------------------------------------------------------

    if _looks_like_financial_case(text):

        amount = getattr(parsed_case, "amount", None)
        amount_value = getattr(parsed_case, "amount_value", None)

        if not _has_value(amount) and not _has_value(amount_value):
            missing.append(
                {
                    "field": "amount",
                    "question": _FIELD_HELP["amount"]["question"],
                    "reason": _FIELD_HELP["amount"]["reason"],
                }
            )

    # --------------------------------------------------------
    # 3. Desired outcome
    # --------------------------------------------------------

    resolution = getattr(
        parsed_case,
        "requested_resolution",
        None,
    )

    explicit_problem = any(
        keyword in text
        for keyword in (
            "denied",
            "dispute",
            "complaint",
            "cancelled",
            "canceled",
            "not received",
            "missing",
            "charged",
            "failed",
            "wrong",
            "damaged",
            "broken",
            "refused",
            "rejected",
            "issue",
            "problem",
            "claim",
            "request",
            "need",
            "want",
            "unable",
        )
    )

    if not _has_value(resolution) and not explicit_problem:
        missing.append(
            {
                "field": "requested_resolution",
                "question": _FIELD_HELP["requested_resolution"]["question"],
                "reason": _FIELD_HELP["requested_resolution"]["reason"],
            }
        )

    # --------------------------------------------------------
    # 4. Domain awareness only
    # --------------------------------------------------------

    is_flight = _looks_like_flight_case(text)
    is_insurance = _looks_like_insurance_case(text)
    is_financial = _looks_like_financial_case(text)

    # Reserved for future domain-specific enrichment.
    # These flags intentionally do not create mandatory fields.
    _ = (is_flight, is_insurance, is_financial)

    return {
        "needs_information": bool(missing),
        "missing_information": missing,
    }


def missing_to_json(sufficiency: dict) -> str:
    """
    Serialize evidence-sufficiency information for persistence.
    Kept as a public helper because case_analysis imports it.
    """

    return json.dumps(
        sufficiency,
        ensure_ascii=False,
    )
