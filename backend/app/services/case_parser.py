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


def _elements(response: dict[str, Any]) -> list[dict[str, Any]]:
    return response.get("output", {}).get("elements", [])


def _all_text(response: dict[str, Any]) -> str:
    return "\n".join(
        element.get("text", "")
        for element in _elements(response)
        if isinstance(element, dict)
        and element.get("text")
    )


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

    # Fallback: search entire document.
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

    normalized = (
        text
        .replace("\u00A5", "Y")
        .replace("¥", "Y")
        .strip()
    )

    currency = None

    if "JPY" in normalized.upper():
        currency = "JPY"

    elif "Y" in normalized.upper():
        currency = "JPY"

    elif "¥" in original:
        currency = "JPY"

    # Find numeric amount.
    match = re.search(
        r"\d[\d,]*(?:\.\d+)?",
        normalized,
    )

    if not match:
        return None, currency

    raw = match.group(0)

    # Preserve decimal meaning where relevant.
    if "." in raw:
        cleaned = raw.replace(",", "")
    else:
        cleaned = raw.replace(",", "")

    return cleaned, currency


def _extract_amount(
    text: str,
) -> tuple[str | None, str | None, str | None]:

    # Examples:
    # Amount paid: ¥50,000
    # Amount: Y120,000
    # Paid: JPY 50000
    # Refund amount: ¥50,000

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

    # Explicit Supporting facts field.
    match = re.search(
        r"Supporting facts\s*:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )

    if match:
        value = match.group(1).strip()

        if value:
            facts.append(value)

    # Also support actual list items.
    for line in text.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("- "):
            fact = stripped[2:].strip()

            if fact:
                facts.append(fact)

    # Remove duplicates while preserving order.
    unique_facts = []

    for fact in facts:

        if fact not in unique_facts:
            unique_facts.append(fact)

    return unique_facts


def parse_case(
    response: dict[str, Any],
) -> Case:

    text = _all_text(response)

    # --------------------------------------------------------
    # PASSENGER
    # --------------------------------------------------------

    passenger = _find_line(
        text,
        "Passenger",
        "Passenger name",
        "Name",
    )

    # --------------------------------------------------------
    # BOOKING REFERENCE
    # --------------------------------------------------------

    booking_reference = _find_line(
        text,
        "Booking reference",
        "Booking Reference",
        "Booking ref",
        "Reference",
    )

    # --------------------------------------------------------
    # AIRLINE
    # --------------------------------------------------------

    airline = _find_line(
        text,
        "Airline",
        "Airline name",
    )

    # --------------------------------------------------------
    # FLIGHT NUMBER
    # --------------------------------------------------------

    flight_number = _extract_flight_number(
        text
    )

    # --------------------------------------------------------
    # CANCELLATION DATE
    # --------------------------------------------------------

    cancellation_date = _find_line(
        text,
        "Cancellation date",
        "Flight cancellation date",
        "Cancelled date",
        "Cancellation Date",
    )

    # --------------------------------------------------------
    # AMOUNT
    # --------------------------------------------------------

    (
        amount,
        amount_value,
        amount_currency,
    ) = _extract_amount(text)

    # --------------------------------------------------------
    # REFUND
    # --------------------------------------------------------

    refund_received = _extract_refund_received(
        text
    )

    # --------------------------------------------------------
    # REQUESTED RESOLUTION
    # --------------------------------------------------------

    requested_resolution = _find_line(
        text,
        "Requested resolution",
        "Requested Resolution",
        "Resolution requested",
        "Desired resolution",
    )

    # --------------------------------------------------------
    # SUPPORTING FACTS
    # --------------------------------------------------------

    supporting_facts = _extract_supporting_facts(
        text
    )

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
    )