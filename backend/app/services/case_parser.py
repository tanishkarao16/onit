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


def _extract_flight_number(text: str) -> str | None:
    # match IATA code + number like NH123 or NH 123
    m = re.search(r"\b([A-Z]{2}\s?\d{1,4})\b", text)
    if m:
        return m.group(1).replace(" ", "")
    return None


def _normalize_amount(text: str) -> tuple[str | None, str | None]:
    # simple normalization for JPY-like formats: ¥120,000 or Y120,000 or JPY 120000
    if not text:
        return None, None
    t = text.replace("\u00A5", "Y")
    # find currency symbol
    cur = None
    if "Y" in t or "\u00A5" in text:
        cur = "JPY"
    # numbers
    num = None
    m = re.search(r"([0-9][0-9,\.]+)", t)
    if m:
        raw = m.group(1)
        cleaned = raw.replace(",", "").replace(".", "")
        num = cleaned
    if num:
        return num, cur
    return None, None


def _elements(response: dict[str, Any]) -> list[dict[str, Any]]:
    return response.get("output", {}).get("elements", [])


def _all_text(response: dict[str, Any]) -> str:
    return "\n".join(
        element.get("text", "")
        for element in _elements(response)
        if element.get("text")
    )


def _find_line(text: str, label: str) -> str | None:
    pattern = rf"^{re.escape(label)}:\s*(.+)$"

    for line in text.splitlines():
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def parse_case(response: dict[str, Any]) -> Case:
    text = _all_text(response)

    passenger = None
    booking_reference = None

    passenger_match = re.search(
        r"Passenger:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    if passenger_match:
        passenger = passenger_match.group(1).strip()

    booking_match = re.search(
        r"Booking reference:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    if booking_match:
        booking_reference = booking_match.group(1).strip()

    airline = _find_line(text, "Airline")
    cancellation_date = _find_line(text, "Flight cancellation date")
    flight_number = _extract_flight_number(text)

    amount = None
    amount_value = None
    amount_currency = None
    amount_match = re.search(
        r"(?:Amount paid|paid)\s*:\s*([^\s]+)",
        text,
        re.IGNORECASE,
    )
    if amount_match:
        amount = amount_match.group(1).strip()
        # normalize amount/currency if possible (kept separate from stored amount)
        norm_amount, norm_currency = _normalize_amount(amount)
        if norm_amount and norm_currency:
            amount_value = norm_amount
            amount_currency = norm_currency

    refund_received = None

    refund_match = re.search(
        r"Refund received:\s*(Yes|No)",
        text,
        re.IGNORECASE,
    )

    if refund_match:
        refund_received = (
            refund_match.group(1).strip().lower() == "yes"
        )

    requested_resolution = None

    resolution_match = re.search(
        r"Requested resolution:\s*\n?\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )

    if resolution_match:
        requested_resolution = resolution_match.group(1).strip()

    supporting_facts = []

    for element in _elements(response):
        element_text = element.get("text", "")

        if element.get("role") == "ListItem" and element_text:
            supporting_facts.append(
                element_text.lstrip("- ").strip()
            )

    return Case(
        passenger=passenger,
        booking_reference=booking_reference,
        airline=airline,
        flight_number=flight_number,
        cancellation_date=cancellation_date,
        amount=amount,
        amount_value=amount_value,
        amount_currency=amount_currency,
        refund_received=refund_received,
        requested_resolution=requested_resolution,
        supporting_facts=supporting_facts,
    )
