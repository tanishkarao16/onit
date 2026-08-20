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
    amount: str | None = None
    refund_received: bool | None = None
    requested_resolution: str | None = None
    supporting_facts: list[str] | None = None


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

    amount = None
    amount_match = re.search(
        r"(?:Amount paid|paid)\s*:\s*([^\s]+)",
        text,
        re.IGNORECASE,
    )
    if amount_match:
        amount = amount_match.group(1).strip()

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
        cancellation_date=cancellation_date,
        amount=amount,
        refund_received=refund_received,
        requested_resolution=requested_resolution,
        supporting_facts=supporting_facts,
    )
