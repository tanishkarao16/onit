import json
from typing import Any


# Generic mapping of fields to human questions and reasons
_FIELD_HELP = {
    "passenger": {
        "question": "Who is the affected person?",
        "reason": "Needed to identify the individual involved in the case.",
    },
    "booking_reference": {
        "question": "What is the booking reference?",
        "reason": "Required to identify the case and determine the applicable process.",
    },
    "organization": {
        "question": "Which organization or provider is this about?",
        "reason": "Needed to route the case to the correct handler.",
    },
    "airline": {
        "question": "Which airline or carrier is this about?",
        "reason": "Needed to contact the correct provider and locate records.",
    },
    "amount": {
        "question": "What is the amount involved?",
        "reason": "Required to quantify the claim and determine remediation steps.",
    },
    "requested_resolution": {
        "question": "What resolution is being requested?",
        "reason": "Clarifies the desired outcome for resolving the case.",
    },
}


def evaluate_evidence_sufficiency(parsed_case: Any) -> dict:
    """
    Determine whether the parsed case has enough information to make a reliable
    decision. Returns a dict with keys:
      - needs_information: bool
      - missing_information: list[ {field, question, reason} ]

    This is intentionally generic. It flags missing identity fields (passenger
    or booking_reference or organization) and some common case attributes like
    amount or requested_resolution when they are relevant.
    """

    missing = []

    # Identity: require at least one identifier
    identity_fields = ["passenger", "booking_reference", "organization", "airline"]
    has_identity = any(
        bool(getattr(parsed_case, f, None))
        for f in identity_fields
    )

    if not has_identity:
        for f in ["passenger", "booking_reference"]:
            missing.append({
                "field": f,
                "question": _FIELD_HELP.get(f, {}).get("question", f"Provide {f}."),
                "reason": _FIELD_HELP.get(f, {}).get("reason", "Required to identify the case."),
            })
        # When identity is missing, also request what resolution is desired
        missing.append({
            "field": "requested_resolution",
            "question": _FIELD_HELP.get("requested_resolution", {}).get("question", "What resolution is requested?"),
            "reason": _FIELD_HELP.get("requested_resolution", {}).get("reason", "Clarifies the desired outcome."),
        })

    # If this appears to be a monetary claim, prefer amount
    amount_like = bool(getattr(parsed_case, "amount", None)) or bool(getattr(parsed_case, "amount_value", None))
    # If supporting facts mention 'refund' or 'refund' keywords, ensure amount present
    facts = getattr(parsed_case, "supporting_facts", []) or []
    facts_text = " ".join(facts).lower() if isinstance(facts, list) else str(facts).lower()

    if ("refund" in facts_text or "refund" in (getattr(parsed_case, "requested_resolution", "") or "").lower()) and not amount_like:
        f = "amount"
        missing.append({
            "field": f,
            "question": _FIELD_HELP.get(f, {}).get("question", f"What is the {f} ?"),
            "reason": _FIELD_HELP.get(f, {}).get("reason", "Needed to quantify the claim."),
        })

    # Do not require `requested_resolution` by default; it's only required when
    # the case context explicitly indicates a desired outcome was mentioned.

    # Deduplicate by field
    seen = set()
    dedup = []
    for m in missing:
        if m["field"] in seen:
            continue
        seen.add(m["field"])
        dedup.append(m)

    needs = len(dedup) > 0

    return {
        "needs_information": needs,
        "missing_information": dedup,
    }


def missing_to_json(missing_info: dict) -> str:
    try:
        return json.dumps(missing_info, ensure_ascii=False)
    except Exception:
        return ""
