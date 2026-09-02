from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings


# ============================================================
# ERRORS
# ============================================================

class NutrientError(Exception):
    """Raised when Nutrient document extraction fails."""


# ============================================================
# NUTRIENT CONFIGURATION
# ============================================================

NUTRIENT_EXTRACT_URL = (
    settings.nutrient_api_url.rstrip("/")
    if getattr(settings, "nutrient_api_url", "")
    else "https://api.nutrient.io/extraction/extract"
)


# ============================================================
# ONIT EXTRACTION SCHEMA
# ============================================================

ONIT_EXTRACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "passenger": {
            "type": "string",
            "description": "Full name of the passenger.",
        },
        "airline": {
            "type": "string",
            "description": "Name of the airline or organization.",
        },
        "booking_reference": {
            "type": "string",
            "description": "Booking reference or reservation code.",
        },
        "flight_number": {
            "type": "string",
            "description": "Flight number.",
        },
        "cancellation_date": {
            "type": "string",
            "description": "Date when the flight was cancelled.",
        },
        "amount_paid": {
            "type": "string",
            "description": "Original amount paid.",
        },
        "refund_received": {
            "type": "string",
            "description": "Whether a refund has been received.",
        },
        "reason_for_cancellation": {
            "type": "string",
            "description": "Reason for the cancellation.",
        },
        "requested_resolution": {
            "type": "string",
            "description": "Resolution requested by the passenger.",
        },
        "supporting_facts": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "Important facts supporting the case.",
        },
        "contact_date": {
            "type": "string",
            "description": "Date the passenger contacted the organization.",
        },
    },
}


# ============================================================
# MIME TYPES
# ============================================================

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".doc": "application/msword",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".xls": "application/vnd.ms-excel",
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def _get_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in MIME_TYPES:
        return MIME_TYPES[suffix]

    guessed, _ = mimetypes.guess_type(str(path))

    return guessed or "application/octet-stream"


# ============================================================
# GENERAL HELPERS
# ============================================================

def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (int, float)):
        return str(value)

    value = str(value).strip()

    return value if value else None


def _normalise_key(key: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(key).lower(),
    ).strip("_")


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        parts = []

        for item in value:
            text = _flatten_text(item)

            if text:
                parts.append(text)

        return "\n".join(parts)

    if isinstance(value, dict):
        parts = []

        for key, item in value.items():
            text = _flatten_text(item)

            if text:
                parts.append(f"{key}: {text}")

        return "\n".join(parts)

    return str(value).strip()


# ============================================================
# LOCAL TEXT FILE SUPPORT
# ============================================================

def _read_text_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(
            encoding="utf-8",
        )
    except UnicodeDecodeError:
        try:
            return path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            return None
    except Exception:
        return None


# ============================================================
# NUTRIENT RESPONSE NORMALIZATION
# ============================================================

def _extract_structured_data(
    nutrient_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize Nutrient's response into ONIT's known schema.

    Handles both:

        {
            "passenger": "...",
            "airline": "..."
        }

    and nested forms such as:

        {
            "data": {...}
        }

        {
            "result": {...}
        }

        {
            "output": {
                "data": {...}
            }
        }
    """

    schema_keys = set(
        ONIT_EXTRACTION_SCHEMA["properties"].keys()
    )

    # --------------------------------------------------------
    # 1. Top-level response
    # --------------------------------------------------------

    direct = {}

    for key in schema_keys:
        if key in nutrient_response:
            direct[key] = nutrient_response[key]

    if direct:
        return direct

    # --------------------------------------------------------
    # 2. Candidate nested containers
    # --------------------------------------------------------

    candidates = [
        nutrient_response.get("data"),
        nutrient_response.get("result"),
        nutrient_response.get("extracted_data"),
        nutrient_response.get("output"),
    ]

    output = nutrient_response.get("output")

    if isinstance(output, dict):
        candidates.extend(
            [
                output.get("data"),
                output.get("result"),
                output.get("extracted_data"),
            ]
        )

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        found = {}

        for key in schema_keys:
            if key in candidate:
                found[key] = candidate[key]

        if found:
            return found

        # ----------------------------------------------------
        # Normalized key matching
        # ----------------------------------------------------

        normalized_candidate = {
            _normalise_key(key): value
            for key, value in candidate.items()
        }

        normalized_found = {}

        for key in schema_keys:
            normalized_key = _normalise_key(key)

            if normalized_key in normalized_candidate:
                normalized_found[key] = (
                    normalized_candidate[normalized_key]
                )

        if normalized_found:
            return normalized_found

    return {}


# ============================================================
# STRUCTURED DATA → TEXT
# ============================================================

def _structured_data_to_text(
    extracted: Dict[str, Any],
) -> str:

    labels = {
        "passenger": "Passenger",
        "airline": "Airline",
        "booking_reference": "Booking Reference",
        "flight_number": "Flight Number",
        "cancellation_date": "Cancellation Date",
        "amount_paid": "Amount Paid",
        "refund_received": "Refund Received",
        "reason_for_cancellation": "Reason for Cancellation",
        "requested_resolution": "Requested Resolution",
        "contact_date": "Contact Date",
    }

    ordered_fields = [
        "passenger",
        "airline",
        "booking_reference",
        "flight_number",
        "cancellation_date",
        "amount_paid",
        "refund_received",
        "reason_for_cancellation",
        "requested_resolution",
        "contact_date",
    ]

    lines: List[str] = []

    for field in ordered_fields:

        if field not in extracted:
            continue

        value = extracted.get(field)

        if value is None:
            continue

        text = _flatten_text(value)

        if not text:
            continue

        label = labels.get(
            field,
            field.replace("_", " ").title(),
        )

        lines.append(
            f"{label}: {text}"
        )

    # --------------------------------------------------------
    # Supporting facts
    # --------------------------------------------------------

    supporting_facts = extracted.get(
        "supporting_facts"
    )

    if supporting_facts:

        lines.append(
            "Supporting Facts:"
        )

        if isinstance(
            supporting_facts,
            list,
        ):

            for fact in supporting_facts:

                fact_text = _clean_string(
                    fact
                )

                if fact_text:
                    lines.append(
                        f"- {fact_text}"
                    )

        else:

            fact_text = _flatten_text(
                supporting_facts
            )

            for fact in fact_text.splitlines():

                fact = fact.strip()

                if not fact:
                    continue

                if fact.startswith("-"):
                    lines.append(fact)
                else:
                    lines.append(
                        f"- {fact}"
                    )

    return "\n".join(lines).strip()


# ============================================================
# MAIN NUTRIENT DOCUMENT PARSER
# ============================================================

async def parse_document(
    path: Path,
    mode: str = "understand",
    output_format: str = "spatial",
) -> Dict[str, Any]:

    path = Path(path)

    if not path.exists():
        raise NutrientError(
            f"Document not found: {path}"
        )

    # --------------------------------------------------------
    # Plain text files
    # --------------------------------------------------------

    if path.suffix.lower() in {
        ".txt",
        ".md",
    }:

        text = _read_text_file(path)

        if text is None:
            raise NutrientError(
                f"Unable to read text document: {path.name}"
            )

        return {
            "output": {
                "elements": [
                    {
                        "role": "Text",
                        "text": text,
                    }
                ]
            },
            "extracted_data": {},
            "nutrient_response": None,
            "source": "local_text",
            "status": "COMPLETED",
        }

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    api_key = getattr(
        settings,
        "nutrient_api_key",
        "",
    )

    if not api_key:
        raise NutrientError(
            "NUTRIENT_API_KEY is not configured."
        )

    # --------------------------------------------------------
    # Read document
    # --------------------------------------------------------

    try:
        document = path.read_bytes()
    except Exception as exc:
        raise NutrientError(
            f"Unable to read document {path.name}: {exc}"
        ) from exc

    mime_type = _get_mime_type(path)

    # --------------------------------------------------------
    # Nutrient extraction instructions
    # --------------------------------------------------------

    instructions = {
        "schema": ONIT_EXTRACTION_SCHEMA,
    }

    # --------------------------------------------------------
    # Call Nutrient
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:

            response = await client.post(
                NUTRIENT_EXTRACT_URL,
                headers={
                    "Authorization": (
                        f"Bearer {api_key}"
                    ),
                },
                files={
                    "file": (
                        path.name,
                        document,
                        mime_type,
                    ),
                },
                data={
                    "instructions": json.dumps(
                        instructions,
                        ensure_ascii=False,
                    ),
                },
            )

    except httpx.TimeoutException as exc:

        raise NutrientError(
            "Nutrient API request timed out after 120 seconds."
        ) from exc

    except httpx.HTTPError as exc:

        raise NutrientError(
            f"Nutrient API connection failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # API error
    # --------------------------------------------------------

    if response.status_code >= 400:

        try:
            error_body = response.json()

            error_text = json.dumps(
                error_body,
                ensure_ascii=False,
            )

        except Exception:
            error_text = response.text

        raise NutrientError(
            "Nutrient API request failed with "
            f"status {response.status_code}: "
            f"{error_text}"
        )

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    try:

        nutrient_response = response.json()

    except Exception as exc:

        raise NutrientError(
            "Nutrient API returned invalid JSON."
        ) from exc

    if not isinstance(
        nutrient_response,
        dict,
    ):
        raise NutrientError(
            "Unexpected Nutrient API response format."
        )

    # --------------------------------------------------------
    # Extract structured fields
    # --------------------------------------------------------

    extracted_data = _extract_structured_data(
        nutrient_response
    )

    # --------------------------------------------------------
    # Convert structured fields to text
    # --------------------------------------------------------

    extracted_text = _structured_data_to_text(
        extracted_data
    )

    # --------------------------------------------------------
    # Fallback textual response handling
    # --------------------------------------------------------

    if not extracted_text:

        possible_text = [
            nutrient_response.get("text"),
            nutrient_response.get("markdown"),
            nutrient_response.get("content"),
        ]

        output = nutrient_response.get(
            "output"
        )

        if isinstance(
            output,
            dict,
        ):

            possible_text.extend(
                [
                    output.get("text"),
                    output.get("markdown"),
                    output.get("content"),
                ]
            )

        for candidate in possible_text:

            candidate_text = _flatten_text(
                candidate
            )

            if candidate_text:

                extracted_text = (
                    candidate_text
                )

                break

    # --------------------------------------------------------
    # Build compatibility response
    # --------------------------------------------------------

    elements = []

    if extracted_text:

        elements.append(
            {
                "role": "Text",
                "text": extracted_text,
            }
        )

    status = (
        "COMPLETED"
        if extracted_data or extracted_text
        else "NO_FACTS_DETECTED"
    )

    return {
        "output": {
            "elements": elements,
        },

        "extracted_data": extracted_data,

        "nutrient_response": nutrient_response,

        "source": "nutrient",

        "mode": mode,

        "output_format": output_format,

        "status": status,
    }


# ============================================================
# EXISTING ONIT PARSER HELPERS
# ============================================================

def _find_line(
    text: str,
    label: str,
) -> Optional[str]:

    pattern = (
        rf"(?im)^\s*"
        rf"{re.escape(label)}"
        rf"\s*:\s*(.+?)\s*$"
    )

    match = re.search(
        pattern,
        text,
    )

    if not match:
        return None

    value = match.group(1).strip()

    return value or None


def _extract_amount(
    text: str,
) -> Optional[float]:

    value = _find_line(
        text,
        "Amount Paid",
    )

    if not value:
        return None

    # Keep digits, decimal point and commas.
    cleaned = re.sub(
        r"[^\d.,]",
        "",
        value,
    )

    if not cleaned:
        return None

    cleaned = cleaned.replace(
        ",",
        "",
    )

    try:
        return float(cleaned)

    except ValueError:
        return None


def _extract_refund_received(
    text: str,
) -> Optional[bool]:

    value = _find_line(
        text,
        "Refund Received",
    )

    if value is None:
        return None

    normalized = value.strip().lower()

    if normalized in {
        "yes",
        "true",
        "received",
        "paid",
    }:
        return True

    if normalized in {
        "no",
        "false",
        "not received",
        "unpaid",
        "none",
    }:
        return False

    return None


def _extract_supporting_facts(
    text: str,
) -> List[str]:

    facts: List[str] = []

    lines = text.splitlines()

    inside_supporting_facts = False

    for line in lines:

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.lower().startswith(
            "supporting facts:"
        ):

            inside_supporting_facts = True

            continue

        if inside_supporting_facts:

            # Stop at the next normal field.
            if (
                re.match(
                    r"^[A-Za-z][A-Za-z ]+:\s*.+$",
                    stripped,
                )
                and not stripped.startswith("-")
            ):
                break

            if stripped.startswith("-"):

                fact = stripped[1:].strip()

                if fact:
                    facts.append(fact)

    return facts


def _extract_amount_raw(
    text: str,
) -> Optional[str]:

    return _find_line(
        text,
        "Amount Paid",
    )


# ============================================================
# CASE PARSER
# ============================================================

def parse_case(
    text: str,
) -> Dict[str, Any]:

    if not text:

        return {
            "passenger": None,
            "airline": None,
            "booking_reference": None,
            "flight_number": None,
            "cancellation_date": None,
            "amount_paid": None,
            "amount_paid_raw": None,
            "refund_received": None,
            "reason_for_cancellation": None,
            "requested_resolution": None,
            "supporting_facts": [],
            "contact_date": None,
        }

    passenger = _find_line(
        text,
        "Passenger",
    )

    airline = _find_line(
        text,
        "Airline",
    )

    booking_reference = _find_line(
        text,
        "Booking Reference",
    )

    flight_number = _find_line(
        text,
        "Flight Number",
    )

    cancellation_date = _find_line(
        text,
        "Cancellation Date",
    )

    amount_paid_raw = _extract_amount_raw(
        text
    )

    amount_paid = _extract_amount(
        text
    )

    refund_received = _extract_refund_received(
        text
    )

    reason_for_cancellation = _find_line(
        text,
        "Reason for Cancellation",
    )

    requested_resolution = _find_line(
        text,
        "Requested Resolution",
    )

    contact_date = _find_line(
        text,
        "Contact Date",
    )

    supporting_facts = _extract_supporting_facts(
        text
    )

    return {
        "passenger": passenger,
        "airline": airline,
        "booking_reference": booking_reference,
        "flight_number": flight_number,
        "cancellation_date": cancellation_date,
        "amount_paid": amount_paid,
        "amount_paid_raw": amount_paid_raw,
        "refund_received": refund_received,
        "reason_for_cancellation": reason_for_cancellation,
        "requested_resolution": requested_resolution,
        "supporting_facts": supporting_facts,
        "contact_date": contact_date,
    }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

async def extract_and_parse_case(
    path: Path,
) -> Dict[str, Any]:

    nutrient_result = await parse_document(
        path
    )

    elements = (
        nutrient_result
        .get("output", {})
        .get("elements", [])
    )

    text_parts: List[str] = []

    for element in elements:

        if not isinstance(
            element,
            dict,
        ):
            continue

        text = element.get(
            "text"
        )

        if text:
            text_parts.append(
                str(text)
            )

    extracted_text = "\n".join(
        text_parts
    ).strip()

    parsed_case = parse_case(
        extracted_text
    )

    return {
        "text": extracted_text,
        "parsed_case": parsed_case,
        "extracted_data": (
            nutrient_result.get(
                "extracted_data",
                {},
            )
        ),
        "nutrient_response": (
            nutrient_result.get(
                "nutrient_response"
            )
        ),
        "status": nutrient_result.get(
            "status",
            "UNKNOWN",
        ),
    }