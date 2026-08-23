from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base, engine, get_db
from app.integrations.nutrient import NutrientError, parse_document
from app.models.case import Case, CaseStatus
from app.services.case_parser import parse_case
from app.services.case_persistence import persist_parsed_case


Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/cases", tags=["cases"])


class CreateCaseRequest(BaseModel):
    title: str
    description: str
    organization: str | None = None
    amount: str | None = None
    currency: str | None = None


@router.post("")
def create_case(
    request: CreateCaseRequest,
    db: Session = Depends(get_db),
):
    case = Case(
        title=request.title,
        description=request.description,
        organization=request.organization,
        amount=request.amount,
        currency=request.currency,
        status=CaseStatus.CREATED,
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return {
        "status": "ok",
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "organization": case.organization,
            "amount": case.amount,
            "currency": case.currency,
            "status": case.status,
        },
    }


@router.get("")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()

    return {
        "status": "ok",
        "cases": [
            {
                "id": case.id,
                "title": case.title,
                "description": case.description,
                "organization": case.organization,
                "amount": case.amount,
                "currency": case.currency,
                "status": case.status,
            }
            for case in cases
        ],
    }


@router.get("/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    return {
        "status": "ok",
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "organization": case.organization,
            "amount": case.amount,
            "currency": case.currency,
            "status": case.status,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
        },
    }



@router.post("/parse-and-create")
async def parse_and_create_case(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

        parsed_case = parse_case(nutrient_response)
        case = persist_parsed_case(db, parsed_case)

        return {
            "status": "ok",
            "case": {
                "id": case.id,
                "passenger": case.passenger,
                "booking_reference": case.booking_reference,
                "airline": case.airline,
                "cancellation_date": case.cancellation_date,
                "amount": case.amount,
                "refund_received": case.refund_received,
                "requested_resolution": case.requested_resolution,
                "supporting_facts": parsed_case.supporting_facts,
                "status": case.status,
            },
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except NutrientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


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
