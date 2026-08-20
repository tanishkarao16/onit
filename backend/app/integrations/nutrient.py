from pathlib import Path
import json

import httpx

from app.core.config import settings


NUTRIENT_PARSE_URL = "https://api.nutrient.io/extraction/parse"


class NutrientError(Exception):
    """Raised when Nutrient document processing fails."""


async def parse_document(
    file_path: str | Path,
    mode: str = "understand",
    output_format: str = "spatial",
) -> dict:
    """
    Send a document to Nutrient's Data Extraction Parse API.

    Returns the parsed document response as a Python dictionary.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    if not settings.nutrient_api_key:
        raise NutrientError("NUTRIENT_API_KEY is not configured.")

    instructions = {
        "mode": mode,
        "output": {
            "format": output_format,
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.nutrient_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with path.open("rb") as document:
                response = await client.post(
                    NUTRIENT_PARSE_URL,
                    headers=headers,
                    files={
                        "file": (
                            path.name,
                            document,
                            "application/octet-stream",
                        )
                    },
                    data={
                        "instructions": json.dumps(instructions),
                    },
                )

        if response.is_error:
            raise NutrientError(
                f"Nutrient API returned {response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    except httpx.HTTPError as exc:
        raise NutrientError(
            f"Could not connect to Nutrient: {exc}"
        ) from exc
