from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.integrations.nutrient import NutrientError, parse_document
from app.services.case_parser import parse_case


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/parse")
async def parse_case_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required.")

    suffix = Path(file.filename).suffix or ".bin"

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = Path(temp_file.name)

        try:
            nutrient_response = await parse_document(
                temp_path,
                mode="understand",
                output_format="spatial",
            )
        finally:
            temp_path.unlink(missing_ok=True)

        case = parse_case(nutrient_response)

        return {
            "status": "ok",
            "case": {
                "passenger": case.passenger,
                "booking_reference": case.booking_reference,
                "airline": case.airline,
                "cancellation_date": case.cancellation_date,
                "amount": case.amount,
                "refund_received": case.refund_received,
                "requested_resolution": case.requested_resolution,
                "supporting_facts": case.supporting_facts,
            },
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except NutrientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
