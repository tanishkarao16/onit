from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class Case:
    passenger: str | None = None
    booking_reference: str | None = None
    airline: str | None = None
    cancellation_date: str | None = None
    flight_number: str | None = None

    amount: str | None = None
    amount_value: str | None = None
    amount_currency: str | None = None

    refund_received: bool | None = None
    requested_resolution: str | None = None
    supporting_facts: list[str] | None = None
    # Generic facts mapping (normalized key -> value) to support domain-agnostic analysis
    facts: dict[str, str] | None = None


def _elements(response: dict[str, Any]) -> list[dict[str, Any]]:
    # Support multiple Nutrient response shapes
    direct = response.get("elements")
    if isinstance(direct, list):
        return [e for e in direct if isinstance(e, dict)]

    output = response.get("output")
    if isinstance(output, dict):
        nested = output.get("elements")
        if isinstance(nested, list):
            return [e for e in nested if isinstance(e, dict)]

    return []


def _all_text(response: dict[str, Any]) -> str:
    """
    Flatten elements into readable text; used only as a fallback.
    Prefer structured extraction from elements elsewhere.
    """

    lines: list[str] = []

    for element in _elements(response):
        text = element.get("text")
        if isinstance(text, str) and text.strip():
            # split multi-line element text into separate lines
            for line in text.splitlines():
                cleaned = line.strip()
                if cleaned:
                    lines.append(cleaned)

    # preserve order and unique
    unique: list[str] = []
    for l in lines:
        if l not in unique:
            unique.append(l)

    return "\n".join(unique)


def _parse_elements_to_kv(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert nutrient elements into a list of key/value candidates with provenance.
    Each item: {"key": str|None, "value": str|None, "provenance": {...}}
    """

    out: list[dict[str, Any]] = []

    for idx, element in enumerate(_elements(response)):
        prov = {
            "element_index": idx,
            "confidence": element.get("confidence"),
            "page": element.get("page"),
            "bounds": element.get("bounds") or element.get("points"),
            "role": element.get("role"),
        }

        # 1) explicit pairs structure
        pairs = element.get("pairs")
        if isinstance(pairs, list):
            for pair in pairs:
                if not isinstance(pair, dict):
                    continue
                key = pair.get("key")
                val = pair.get("value")
                if isinstance(key, dict):
                    key = key.get("text") or key.get("label") or key.get("value")
                if isinstance(val, dict):
                    val = val.get("text") or val.get("value")
                if key or val:
                    out.append({"key": (key or None), "value": (val or None), "provenance": prov})

        # 2) role-specific handling (ListItem often contains '- Key: Value')
        role = element.get("role")
        text = element.get("text")
        if isinstance(text, str):
            # split multi-line text
            for line in text.splitlines():
                ln = line.strip()
                if not ln:
                    continue

                # list item starting with '-'
                if ln.startswith("- "):
                    ln2 = ln[2:].strip()
                else:
                    ln2 = ln

                # If the line contains a colon, treat as key:value
                if ":" in ln2:
                    parts = ln2.split(":", 1)
                    k = parts[0].strip()
                    v = parts[1].strip()
                    out.append({"key": (k or None), "value": (v or None), "provenance": prov})
                else:
                    # standalone value
                    out.append({"key": None, "value": ln2, "provenance": prov})

        # 3) children elements (recursively handled)
        children = element.get("children")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                ctext = child.get("text")
                if isinstance(ctext, str):
                    for line in ctext.splitlines():
                        ln = line.strip()
                        if not ln:
                            continue
                        if ":" in ln:
                            parts = ln.split(":", 1)
                            out.append({"key": parts[0].strip(), "value": parts[1].strip(), "provenance": prov})
                        else:
                            out.append({"key": None, "value": ln, "provenance": prov})

    return out


def _find_line(
    text: str,
    *labels: str,
) -> str | None:

    for label in labels:

        pattern = rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$"

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE,
        )

        if match:
            return match.group(1).strip()

    return None


def _extract_flight_number(
    text: str,
) -> str | None:

    # Prefer an explicit Flight number field.
    explicit = _find_line(
        text,
        "Flight number",
        "Flight no",
        "Flight",
    )

    if explicit:
        match = re.search(
            r"\b([A-Z]{2,3}\s?\d{1,4})\b",
            explicit.upper(),
        )

        if match:
            return match.group(1).replace(" ", "")

    match = re.search(
        r"\b([A-Z]{2,3}\s?\d{1,4})\b",
        text.upper(),
    )

    if match:
        return match.group(1).replace(" ", "")

    return None


def _normalize_amount(
    text: str,
) -> tuple[str | None, str | None]:

    if not text:
        return None, None

    original = text

    # Normalize common currency symbols and codes to identify currency
    normalized = text.strip()

    currency = None

    # Map symbols to currency codes. Default for '¥' is JPY (prefer JPY for Yen symbol).
    if re.search(r"\bJPY\b", normalized, re.IGNORECASE):
        currency = "JPY"
    elif "\uFFE5" in normalized or "\uffe5" in normalized:
        currency = "JPY"
    elif "\u00A5" in normalized or "¥" in normalized or "￥" in normalized:
        currency = "JPY"
    elif re.search(r"\bUSD\b", normalized, re.IGNORECASE) or "$" in normalized:
        currency = "USD"
    elif re.search(r"\bEUR\b", normalized, re.IGNORECASE) or "€" in normalized:
        currency = "EUR"
    elif re.search(r"\bGBP\b", normalized, re.IGNORECASE) or "£" in normalized:
        currency = "GBP"

    # Try to find an explicit 3-letter currency code anywhere
    code_match = re.search(r"\b([A-Z]{3})\b", normalized.upper())
    if code_match:
        code = code_match.group(1).upper()
        # prefer explicit code when detected
        currency = code

    # Extract numeric amount (allow commas and decimals)
    match = re.search(r"[\d,]+(?:\.\d+)?", normalized)

    if not match:
        return None, currency

    raw = match.group(0)

    cleaned = raw.replace(",", "")

    return cleaned, currency


def _extract_amount(
    text: str,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:

    match = re.search(
        r"(?:Amount paid|Amount|Paid|Refund amount)"
        r"\s*:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None, None, None

    raw_amount = match.group(1).strip()

    value, currency = _normalize_amount(
        raw_amount
    )

    return (
        raw_amount,
        value,
        currency,
    )


def _extract_refund_received(
    text: str,
) -> bool | None:

    match = re.search(
        r"Refund received\s*:\s*(Yes|No)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return (
        match.group(1).strip().lower()
        == "yes"
    )


def _extract_supporting_facts(
    text: str,
) -> list[str]:

    facts: list[str] = []

    match = re.search(
        r"Supporting facts\s*:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )

    if match:

        value = match.group(1).strip()

        if value:
            facts.append(value)

    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("- "):

            fact = stripped[2:].strip()

            if fact:
                facts.append(fact)

    unique_facts: list[str] = []

    for fact in facts:

        if fact not in unique_facts:
            unique_facts.append(fact)

    return unique_facts


def parse_case(
    response: dict[str, Any],
) -> Case:

    # First attempt structured extraction from elements
    kvs = _parse_elements_to_kv(response)

    # Helper to look up a value by matching possible labels
    def lookup_label(*labels: str) -> str | None:
        for item in kvs:
            key = item.get("key")
            val = item.get("value")
            if not key or not val:
                continue
            for label in labels:
                if key.strip().lower() == label.strip().lower():
                    return val
        return None

    # Helper to find first standalone value containing a token
    def lookup_contains(token: str) -> str | None:
        for item in kvs:
            key = item.get("key")
            val = item.get("value")
            if key is None and val and token.lower() in val.lower():
                return val
        return None

    # Build a fallback flattened text once for regex-based lookups
    text = _all_text(response)

    # Build generic facts mapping from KV pairs
    facts: dict[str, str] = {}
    for item in kvs:
        k = item.get("key")
        v = item.get("value")
        if not k or not v:
            continue
        # normalize key to snake_case-like identifier
        nk = re.sub(r"[^a-z0-9]+", "_", k.strip().lower()).strip("_")
        if nk:
            # prefer first-seen value for a given normalized key
            if nk not in facts:
                facts[nk] = v

    # --------------------------------------------------------
    # PASSENGER
    # --------------------------------------------------------

    passenger = (
        lookup_label("Passenger", "Passenger name", "Name")
        or _find_line(text, "Passenger", "Passenger name", "Name")
    )

    # --------------------------------------------------------
    # BOOKING REFERENCE
    # --------------------------------------------------------

    booking_reference = (
        lookup_label("Booking reference", "Booking Reference", "Booking ref", "Reference", "PNR", "Confirmation number")
        or _find_line(
            text,
            "Booking reference",
            "Booking Reference",
            "Booking ref",
            "Reference",
        )
    )

    # --------------------------------------------------------
    # AIRLINE
    # --------------------------------------------------------

    airline = (
        lookup_label("Airline", "Airline name", "Carrier")
        or _find_line(text, "Airline", "Airline name")
    )

    # --------------------------------------------------------
    # FLIGHT NUMBER
    # --------------------------------------------------------

    # Flight number: prefer explicit key first
    flight_number = (
        lookup_label("Flight number", "Flight no", "Flight")
        or _extract_flight_number(text)
    )

    # --------------------------------------------------------
    # CANCELLATION DATE
    # --------------------------------------------------------

    cancellation_date = (
        lookup_label("Cancellation date", "Flight cancellation date", "Cancelled date", "Cancellation Date")
        or _find_line(
            text,
            "Cancellation date",
            "Flight cancellation date",
            "Cancelled date",
            "Cancellation Date",
        )
    )

    # --------------------------------------------------------
    # AMOUNT
    # --------------------------------------------------------
    # AMOUNT: prefer structured KV where key contains 'amount' or 'amount paid'
    amount = None
    amount_value = None
    amount_currency = None

    for item in kvs:
        key = item.get("key")
        val = item.get("value")
        if not key or not val:
            continue
        if "amount" in key.lower() or "paid" in key.lower() or "refund" in key.lower():
            amount = val
            # normalize
            v, c = _normalize_amount(val)
            amount_value = v
            amount_currency = c
            break

    if not amount:
        (
            amount,
            amount_value,
            amount_currency,
        ) = _extract_amount(text)

    # --------------------------------------------------------
    # REFUND
    # --------------------------------------------------------

    # refund_received: prefer structured KV
    refund_received = None
    rr = lookup_label("Refund received")
    if rr is not None:
        refund_received = rr.strip().lower() == "yes"
    else:
        refund_received = _extract_refund_received(text)

    # --------------------------------------------------------
    # REQUESTED RESOLUTION
    # --------------------------------------------------------

    requested_resolution = (
        lookup_label("Requested resolution", "Requested Resolution", "Resolution requested", "Desired resolution", "Requested outcome")
        or _find_line(
            text,
            "Requested resolution",
            "Requested Resolution",
            "Resolution requested",
            "Desired resolution",
        )
    )

    # --------------------------------------------------------
    # SUPPORTING FACTS
    # --------------------------------------------------------

    # supporting facts: collect list items and any KV values under 'Supporting facts'
    supporting_facts = []

    # collect explicit supporting facts from KV pairs
    for item in kvs:
        k = item.get("key")
        v = item.get("value")
        prov = item.get("provenance") or {}
        role = prov.get("role")

        # List items under the 'Supporting facts' section are usually role==ListItem
        if role == "ListItem" and v:
            if k:
                entry = f"{k}: {v}"
                if entry not in supporting_facts:
                    supporting_facts.append(entry)
            else:
                if v not in supporting_facts:
                    supporting_facts.append(v)
            continue

        if not k and v:
            # standalone text block
            if v not in supporting_facts:
                supporting_facts.append(v)
        elif k and "support" in k.lower():
            # value may be multi-line, split into bullets
            if not v:
                continue
            parts = [p.strip() for p in v.split("\n") if p.strip()]
            for p in parts:
                if p not in supporting_facts:
                    supporting_facts.append(p)

    # fallback to regex-based extraction
    if not supporting_facts:
        supporting_facts = _extract_supporting_facts(text)

    return Case(
        passenger=passenger,
        booking_reference=booking_reference,
        airline=airline,
        cancellation_date=cancellation_date,
        flight_number=flight_number,
        amount=amount,
        amount_value=amount_value,
        amount_currency=amount_currency,
        refund_received=refund_received,
        requested_resolution=requested_resolution,
        supporting_facts=supporting_facts,
        facts=facts or None,
    )
