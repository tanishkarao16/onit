from pathlib import Path
from tempfile import NamedTemporaryFile
import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    Request,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base, engine, get_db

from app.integrations.nutrient import (
    NutrientError,
    parse_document,
)

from app.models.case import (
    Case,
    CaseActivity,
    CaseEvidence,
    CaseResearch,
    CaseResponse,
    CaseStatus,
)

from app.services.case_analysis import analyze_case

from app.services.case_response import (
    record_case_response,
    send_case_follow_up,
)


from app.services.case_approval import (
    approve_case,
    request_case_approval,
)

from app.services.case_decision import CaseDecision

from app.services.case_parser import parse_case

from app.services.case_persistence import (
    persist_parsed_case,
)

from app.services.case_planning import plan_case

from app.services.case_research import (
    research_case,
)

from app.services.case_activity import (
    record_activity,
)

import json as _json

 
from app.services.evidence_to_decision import (
    synthesize_evidence_and_plan,
)

from app.services.case_execution import (
    execute_case,
)
 
# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/cases",
    tags=["cases"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class CreateCaseRequest(BaseModel):
    title: str
    description: str
    organization: str | None = None
    amount: str | None = None
    currency: str | None = None


# ============================================================
# CREATE CASE
# ============================================================

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

    record_activity(
        db=db,
        case_id=case.id,
        event_type="CASE_CREATED",
        message="ONIT created a new case.",
    )

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


# ============================================================
# LIST CASES
# ============================================================

@router.get("")
def list_cases(
    db: Session = Depends(get_db),
):

    cases = (
        db.query(Case)
        .order_by(
            Case.created_at.desc()
        )
        .all()
    )

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


# ============================================================
# UNIVERSAL PARSE
#
# PDF / IMAGE -> EXTRACTED CASE DATA
# ============================================================

@router.post("/parse")
async def parse_case_document(
    file: UploadFile = File(...),
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A file is required.",
        )

    suffix = (
        Path(file.filename).suffix
        or ".bin"
    )

    allowed = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
    }

    if suffix.lower() not in allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Use PDF, PNG, JPG, or JPEG."
            ),
        )

    with NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:

        temp_file.write(
            await file.read()
        )

        temp_path = Path(
            temp_file.name
        )

    try:

        nutrient_response = await parse_document(
            temp_path,
            mode="understand",
            output_format="spatial",
        )

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except NutrientError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    finally:

        temp_path.unlink(
            missing_ok=True
        )

    case = parse_case(
        nutrient_response
    )

    return {
        "status": "ok",
        "case": {
            "passenger": case.passenger,
            "booking_reference": (
                case.booking_reference
            ),
            "airline": case.airline,
            "flight_number": getattr(
                case,
                "flight_number",
                None,
            ),
            "cancellation_date": (
                case.cancellation_date
            ),
            "amount": case.amount,
            "amount_value": getattr(
                case,
                "amount_value",
                None,
            ),
            "amount_currency": getattr(
                case,
                "amount_currency",
                None,
            ),
            "refund_received": (
                case.refund_received
            ),
            "requested_resolution": (
                case.requested_resolution
            ),
            "supporting_facts": (
                case.supporting_facts
            ),
        },
    }


# ============================================================
# UNIVERSAL PARSE + CREATE
#
# PDF / IMAGE / PASTED TEXT
# ->
# Nutrient
# ->
# Parsed Case
# ->
# Persistent ONIT Case
# ->
# Evidence
# ->
# Provenance
# ============================================================

@router.post("/parse-and-create")
async def parse_and_create_case(
    request: Request,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):

    try:

        # ======================================================
        # 1. INPUT
        # ======================================================

        if file is None:

            text_input = None

            # ------------------------------
            # JSON
            # ------------------------------

            try:

                body = await request.json()

                if isinstance(body, dict):

                    text_input = body.get(
                        "text"
                    )

            except Exception:
                pass

            # ------------------------------
            # FORM
            # ------------------------------

            if not text_input:

                try:

                    form = await request.form()

                    text_input = form.get(
                        "text"
                    )

                except Exception:
                    pass

            if not text_input:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A file or text is required."
                    ),
                )

            nutrient_response = {
                "output": {
                    "elements": [
                        {
                            "role": "Text",
                            "text": str(
                                text_input
                            ),
                        }
                    ]
                }
            }

            filename = "pasted_text.txt"
            mimetype = "text/plain"

        else:

            # ==================================================
            # 2. FILE VALIDATION
            # ==================================================

            if not file.filename:

                raise HTTPException(
                    status_code=400,
                    detail="A file is required.",
                )

            suffix = (
                Path(file.filename).suffix
                or ".bin"
            )

            allowed = {
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
            }

            if suffix.lower() not in allowed:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Unsupported file type. "
                        "Use PDF, PNG, JPG, or JPEG."
                    ),
                )

            # ==================================================
            # 3. TEMP FILE
            # ==================================================

            with NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:

                temp_file.write(
                    await file.read()
                )

                temp_path = Path(
                    temp_file.name
                )

            filename = file.filename
            mimetype = file.content_type

            # ==================================================
            # 4. NUTRIENT
            # ==================================================

            try:

                nutrient_response = (
                    await parse_document(
                        temp_path,
                        mode="understand",
                        output_format="spatial",
                    )
                )

            except FileNotFoundError as exc:

                raise HTTPException(
                    status_code=400,
                    detail=str(exc),
                ) from exc

            except NutrientError as exc:

                raise HTTPException(
                    status_code=502,
                    detail=str(exc),
                ) from exc

            finally:

                temp_path.unlink(
                    missing_ok=True
                )

        # ======================================================
        # 5. EXTRACT TEXT
        # ======================================================

        elements = (
            nutrient_response
            .get("output", {})
            .get("elements", [])
        )

        original_text = "\n".join(
            element.get("text", "")
            for element in elements
            if isinstance(
                element,
                dict,
            )
        )

        # ======================================================
        # 6. PARSE CASE
        # ======================================================

        parsed_case = parse_case(
            nutrient_response
        )

        # ======================================================
        # 7. PERSIST CASE
        # ======================================================

        case = persist_parsed_case(
            db,
            parsed_case,
        )

        # ======================================================
        # 8. PROVENANCE
        # ======================================================

        def find_provenance_for(value):

            if not value:
                return None

            value_string = str(value)

            for index, element in enumerate(
                elements
            ):

                if not isinstance(
                    element,
                    dict,
                ):
                    continue

                text = element.get(
                    "text",
                    "",
                )

                if value_string in text:

                    provenance = {
                        "source": filename,
                        "element_index": index,
                    }

                    if "confidence" in element:

                        provenance[
                            "confidence"
                        ] = element.get(
                            "confidence"
                        )

                    if "page" in element:

                        provenance[
                            "page"
                        ] = element.get(
                            "page"
                        )

                    return provenance

            return {
                "source": filename,
            }

        # ======================================================
        # 9. FACTS
        # ======================================================

        facts = {

            "passenger": {
                "value": parsed_case.passenger,
                "provenance": find_provenance_for(
                    parsed_case.passenger
                ),
            },

            "booking_reference": {
                "value": (
                    parsed_case.booking_reference
                ),
                "provenance": find_provenance_for(
                    parsed_case.booking_reference
                ),
            },

            "airline": {
                "value": parsed_case.airline,
                "provenance": find_provenance_for(
                    parsed_case.airline
                ),
            },

            "flight_number": {
                "value": getattr(
                    parsed_case,
                    "flight_number",
                    None,
                ),
                "provenance": find_provenance_for(
                    getattr(
                        parsed_case,
                        "flight_number",
                        None,
                    )
                ),
            },

            "cancellation_date": {
                "value": (
                    parsed_case.cancellation_date
                ),
                "provenance": find_provenance_for(
                    parsed_case.cancellation_date
                ),
            },

            "amount": {
                "value": parsed_case.amount,
                "amount_value": getattr(
                    parsed_case,
                    "amount_value",
                    None,
                ),
                "currency": getattr(
                    parsed_case,
                    "amount_currency",
                    None,
                ),
                "provenance": find_provenance_for(
                    parsed_case.amount
                ),
            },

            "refund_received": {
                "value": (
                    parsed_case.refund_received
                ),
                "provenance": find_provenance_for(
                    parsed_case.refund_received
                ),
            },

            "requested_resolution": {
                "value": (
                    parsed_case.requested_resolution
                ),
                "provenance": find_provenance_for(
                    parsed_case.requested_resolution
                ),
            },

            "supporting_facts": {
                "value": (
                    parsed_case.supporting_facts
                ),
                "provenance": {
                    "source": filename,
                },
            },
        }

        # ======================================================
        # 10. EVIDENCE TYPE
        # ======================================================

        if mimetype == "text/plain":

            evidence_type = "text"

        elif (
            mimetype
            and "pdf" in mimetype.lower()
        ):

            evidence_type = "pdf"

        elif (
            mimetype
            and mimetype.lower().startswith(
                "image/"
            )
        ):

            evidence_type = "image"

        else:

            evidence_type = "file"

        # ======================================================
        # 11. EVIDENCE
        # ======================================================

        evidence = CaseEvidence(
            case_id=case.id,
            filename=filename,
            evidence_type=evidence_type,
            mimetype=mimetype,
            original_text=original_text,
            extracted_text=original_text,
            extraction_status="COMPLETED",
            extracted_facts=json.dumps(
                facts,
                ensure_ascii=False,
            ),
        )

        db.add(evidence)

        # ======================================================
        # 12. CONFLICT TRACKING
        # ======================================================

        conflicts = {}

        def try_set(
            field_name,
            value,
        ):

            if value is None:
                return

            if value == "":
                return

            existing = getattr(
                case,
                field_name,
                None,
            )

            if existing in (
                None,
                "",
                [],
            ):

                setattr(
                    case,
                    field_name,
                    value,
                )

            elif str(existing) != str(value):

                conflicts[field_name] = {
                    "existing": existing,
                    "extracted": value,
                }

        # ======================================================
        # 13. IMPORTANT:
        # ACTUALLY APPLY EXTRACTED FACTS TO CASE
        # ======================================================

        try_set(
            "passenger",
            parsed_case.passenger,
        )

        try_set(
            "booking_reference",
            parsed_case.booking_reference,
        )

        try_set(
            "airline",
            parsed_case.airline,
        )

        try_set(
            "cancellation_date",
            parsed_case.cancellation_date,
        )

        try_set(
            "amount",
            getattr(
                parsed_case,
                "amount_value",
                None,
            )
            or parsed_case.amount,
        )

        try_set(
            "currency",
            getattr(
                parsed_case,
                "amount_currency",
                None,
            ),
        )

        try_set(
            "refund_received",
            parsed_case.refund_received,
        )

        try_set(
            "requested_resolution",
            parsed_case.requested_resolution,
        )

        # ======================================================
        # 14. SUPPORTING FACTS
        # ======================================================

        if parsed_case.supporting_facts:

            existing_facts = []

            if case.supporting_facts:

                try:

                    existing_facts = json.loads(
                        case.supporting_facts
                    )

                except (
                    json.JSONDecodeError,
                    TypeError,
                ):

                    existing_facts = []

            if not isinstance(
                existing_facts,
                list,
            ):

                existing_facts = []

            merged_facts = list(
                existing_facts
            )

            for fact in (
                parsed_case.supporting_facts
            ):

                if fact not in merged_facts:

                    merged_facts.append(
                        fact
                    )

            case.supporting_facts = json.dumps(
                merged_facts,
                ensure_ascii=False,
            )

        # ======================================================
        # 15. COMMIT
        # ======================================================

        db.commit()

        db.refresh(case)
        db.refresh(evidence)

        # ======================================================
        # 16. ACTIVITY
        # ======================================================

        record_activity(
            db=db,
            case_id=case.id,
            event_type="EVIDENCE_RECEIVED",
            message=(
                f"ONIT received evidence "
                f"{filename} and created a case."
            ),
        )

        record_activity(
            db=db,
            case_id=case.id,
            event_type="DOCUMENT_ANALYZED",
            message=(
                f"ONIT analyzed {filename}."
            ),
        )

        record_activity(
            db=db,
            case_id=case.id,
            event_type="FACTS_EXTRACTED",
            message=(
                "ONIT extracted structured facts "
                "from submitted evidence."
            ),
        )

        # ======================================================
        # 17. RESPONSE
        # ======================================================

        response = {
            "status": "ok",

            "case": {
                "id": case.id,
                "passenger": case.passenger,
                "booking_reference": (
                    case.booking_reference
                ),
                "airline": case.airline,
                "flight_number": getattr(
                    case,
                    "flight_number",
                    None,
                ),
                "cancellation_date": (
                    case.cancellation_date
                ),
                "amount": case.amount,
                "currency": case.currency,
                "refund_received": (
                    case.refund_received
                ),
                "requested_resolution": (
                    case.requested_resolution
                ),
                "supporting_facts": (
                    case.supporting_facts
                ),
                "status": case.status,
            },

            "evidence": {
                "id": evidence.id,
                "filename": evidence.filename,
                "evidence_type": (
                    evidence.evidence_type
                ),
                "mimetype": evidence.mimetype,
                "extraction_status": (
                    evidence.extraction_status
                ),
                "extracted_facts": json.loads(
                    evidence.extracted_facts
                    or "{}"
                ),
                "created_at": evidence.created_at,
            },
        }

        if conflicts:

            response["conflicts"] = conflicts

        return response

    except HTTPException:
        raise

    except FileNotFoundError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except NutrientError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


# ============================================================
# ADD EVIDENCE TO EXISTING CASE
# ============================================================

@router.post("/{case_id}/evidence")
async def add_case_evidence(
    case_id: int,
    request: Request,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    text_input = None
    filename = None
    mimetype = None
    evidence_type = "text"

    # ========================================================
    # FILE
    # ========================================================

    if file is not None:

        filename = file.filename
        mimetype = file.content_type

        suffix = (
            Path(filename or "").suffix
            or ".bin"
        )

        allowed = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
        }

        if suffix.lower() not in allowed:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type.",
            )

        with NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as tmp:

            tmp.write(
                await file.read()
            )

            tmp.flush()

            temp_path = Path(
                tmp.name
            )

        record_activity(
            db=db,
            case_id=case.id,
            event_type=(
                "EVIDENCE_EXTRACTION_STARTED"
            ),
            message=(
                f"ONIT started extracting "
                f"{filename}."
            ),
        )

        try:

            parsed = await parse_document(
                temp_path,
                mode="understand",
                output_format="spatial",
            )

        except NutrientError as exc:

            record_activity(
                db=db,
                case_id=case.id,
                event_type=(
                    "EVIDENCE_EXTRACTION_FAILED"
                ),
                message=(
                    f"Extraction failed for "
                    f"{filename}: {str(exc)}"
                ),
            )

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        finally:

            temp_path.unlink(
                missing_ok=True
            )

        extracted_text = "\n".join(
            element.get("text", "")
            for element in (
                parsed
                .get("output", {})
                .get("elements", [])
            )
            if isinstance(
                element,
                dict,
            )
        )

        original_text = extracted_text

        if (
            mimetype
            and "pdf" in mimetype.lower()
        ):

            evidence_type = "pdf"

        elif (
            mimetype
            and mimetype.lower().startswith(
                "image/"
            )
        ):

            evidence_type = "image"

        else:

            evidence_type = "file"

    # ========================================================
    # TEXT
    # ========================================================

    else:

        try:

            body = await request.json()

            if isinstance(
                body,
                dict,
            ):

                text_input = body.get(
                    "text"
                )

        except Exception:

            try:

                form = await request.form()

                text_input = form.get(
                    "text"
                )

            except Exception:

                text_input = None

        if not text_input:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No file or text provided."
                ),
            )

        extracted_text = str(
            text_input
        )

        original_text = extracted_text

        filename = "pasted_text.txt"
        mimetype = "text/plain"
        evidence_type = "text"

    # ========================================================
    # PARSE
    # ========================================================

    response = {
        "output": {
            "elements": [
                {
                    "role": "Text",
                    "text": extracted_text,
                }
            ]
        }
    }

    parsed_case = parse_case(
        response
    )

    # ========================================================
    # FACTS
    # ========================================================

    facts = {

        "passenger": parsed_case.passenger,

        "airline": parsed_case.airline,

        "booking_reference": (
            parsed_case.booking_reference
        ),

        "flight_number": getattr(
            parsed_case,
            "flight_number",
            None,
        ),

        "cancellation_date": (
            parsed_case.cancellation_date
        ),

        "amount": parsed_case.amount,

        "amount_value": getattr(
            parsed_case,
            "amount_value",
            None,
        ),

        "amount_currency": getattr(
            parsed_case,
            "amount_currency",
            None,
        ),

        "refund_received": (
            parsed_case.refund_received
        ),

        "requested_resolution": (
            parsed_case.requested_resolution
        ),

        "supporting_facts": (
            parsed_case.supporting_facts
        ),
    }

    # ========================================================
    # SAVE EVIDENCE
    # ========================================================

    evidence = CaseEvidence(
        case_id=case.id,
        filename=filename,
        evidence_type=evidence_type,
        mimetype=mimetype,
        original_text=original_text,
        extracted_text=extracted_text,
        extraction_status="COMPLETED",
        extracted_facts=json.dumps(
            facts,
            ensure_ascii=False,
        ),
    )

    db.add(evidence)

    # ========================================================
    # CONFLICTS
    # ========================================================

    conflicts = {}

    def try_set(
        field_name,
        value,
    ):

        if value is None:
            return

        if value == "":
            return

        existing = getattr(
            case,
            field_name,
            None,
        )

        if existing in (
            None,
            "",
            [],
        ):

            setattr(
                case,
                field_name,
                value,
            )

        elif str(existing) != str(value):

            conflicts[field_name] = {
                "existing": existing,
                "extracted": value,
            }

    # ========================================================
    # UPDATE CASE
    # ========================================================

    try_set(
        "passenger",
        parsed_case.passenger,
    )

    try_set(
        "airline",
        parsed_case.airline,
    )

    try_set(
        "booking_reference",
        parsed_case.booking_reference,
    )

    try_set(
        "cancellation_date",
        parsed_case.cancellation_date,
    )

    try_set(
        "amount",
        getattr(
            parsed_case,
            "amount_value",
            None,
        )
        or parsed_case.amount,
    )

    try_set(
        "currency",
        getattr(
            parsed_case,
            "amount_currency",
            None,
        ),
    )

    try_set(
        "refund_received",
        parsed_case.refund_received,
    )

    try_set(
        "requested_resolution",
        parsed_case.requested_resolution,
    )

    # ========================================================
    # SUPPORTING FACTS
    # ========================================================

    if parsed_case.supporting_facts:

        existing_facts = []

        if case.supporting_facts:

            try:

                existing_facts = json.loads(
                    case.supporting_facts
                )

            except (
                json.JSONDecodeError,
                TypeError,
            ):

                existing_facts = []

        if not isinstance(
            existing_facts,
            list,
        ):

            existing_facts = []

        merged_facts = list(
            existing_facts
        )

        for fact in (
            parsed_case.supporting_facts
        ):

            if fact not in merged_facts:

                merged_facts.append(
                    fact
                )

        case.supporting_facts = json.dumps(
            merged_facts,
            ensure_ascii=False,
        )

    # ========================================================
    # COMMIT
    # ========================================================

    db.commit()

    db.refresh(evidence)
    db.refresh(case)

    # Also apply the same missing_information clear logic used above for parse-and-create
    try:
        if case.missing_information:
            import json as _json

            miss = _json.loads(case.missing_information or "{}")

            missing_fields = [m.get("field") for m in (miss.get("missing_information") or []) if isinstance(m, dict)]

            still_missing = []
            for f in missing_fields:
                if not getattr(case, f, None):
                    still_missing.append(f)

            if not still_missing:
                case.missing_information = None
                case.status = CaseStatus.CREATED
                db.commit()
                db.refresh(case)
    except Exception:
        pass

    # (duplicate cleanup removed — single cleanup already executed above)

    # ========================================================
    # ACTIVITY
    # ========================================================

    record_activity(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_ADDED",
        message=(
            f"ONIT added evidence "
            f"{filename or 'text input'}."
        ),
    )

    record_activity(
        db=db,
        case_id=case.id,
        event_type=(
            "EVIDENCE_EXTRACTION_COMPLETED"
        ),
        message=(
            f"ONIT extracted facts from "
            f"{filename or 'text input'}."
        ),
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    result = {
        "id": evidence.id,
        "case_id": evidence.case_id,
        "filename": evidence.filename,
        "evidence_type": evidence.evidence_type,
        "mimetype": evidence.mimetype,
        "extraction_status": (
            evidence.extraction_status
        ),
        "extracted_facts": json.loads(
            evidence.extracted_facts
            or "{}"
        ),
        "created_at": evidence.created_at,
    }

    if conflicts:

        result["conflicts"] = conflicts

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "passenger": case.passenger,
            "booking_reference": (
                case.booking_reference
            ),
            "airline": case.airline,
            "cancellation_date": (
                case.cancellation_date
            ),
            "amount": case.amount,
            "currency": case.currency,
            "refund_received": (
                case.refund_received
            ),
            "requested_resolution": (
                case.requested_resolution
            ),
            "supporting_facts": (
                case.supporting_facts
            ),
        },

        "evidence": result,
    }


# ============================================================
# GET CASE ACTIVITY
# ============================================================

@router.get("/{case_id}/activity")
def get_case_activity(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    activities = (
        db.query(CaseActivity)
        .filter(
            CaseActivity.case_id == case_id
        )
        .order_by(
            CaseActivity.created_at.asc(),
            CaseActivity.id.asc(),
        )
        .all()
    )

    return {
        "status": "ok",
        "activities": [
            {
                "id": activity.id,
                "event_type": activity.event_type,
                "message": activity.message,
                "created_at": activity.created_at,
            }
            for activity in activities
        ],
    }


# ============================================================
# GET CASE RESEARCH
# ============================================================

@router.get("/{case_id}/research")
def get_case_research(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    research = (
        db.query(CaseResearch)
        .filter(
            CaseResearch.case_id == case_id
        )
        .order_by(
            CaseResearch.created_at.asc(),
            CaseResearch.id.asc(),
        )
        .all()
    )

    return {
        "status": "ok",

        "research": [
            {
                "id": item.id,
                "source": item.source,
                "title": item.title,
                "summary": item.summary,
                "relevance": item.relevance,
                "url": getattr(
                    item,
                    "url",
                    None,
                ),
                "created_at": item.created_at,
            }
            for item in research
        ],
    }


# ============================================================
# GET CASE EVIDENCE
# ============================================================

@router.get("/{case_id}/evidence")
def get_case_evidence(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    items = (
        db.query(CaseEvidence)
        .filter(
            CaseEvidence.case_id == case_id
        )
        .order_by(
            CaseEvidence.created_at.asc(),
            CaseEvidence.id.asc(),
        )
        .all()
    )

    return {
        "status": "ok",

        "evidence": [
            {
                "id": item.id,
                "filename": item.filename,
                "evidence_type": (
                    item.evidence_type
                ),
                "mimetype": item.mimetype,
                "extraction_status": (
                    item.extraction_status
                ),
                "extracted_facts": json.loads(
                    item.extracted_facts
                    or "{}"
                ),
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


# ============================================================
# ANALYZE
# ============================================================

@router.post("/{case_id}/analyze")
def analyze_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:

        decision = analyze_case(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "issue": case.issue,
            "recommended_action": (
                case.recommended_action
            ),
            "priority": case.priority,
            "decision_reason": (
                case.decision_reason
            ),
        },

        "decision": {
            "issue": decision.issue,
            "recommended_action": (
                decision.recommended_action
            ),
            "priority": decision.priority,
            "reason": decision.reason,
        },
    }


# ============================================================
# RESEARCH
# ============================================================

@router.post("/{case_id}/research")
def research_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:

        results = research_case(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
        },

        "research": [
            {
                "source": result.source,
                "title": result.title,
                "summary": result.summary,
                "relevance": result.relevance,
                "url": getattr(
                    result,
                    "url",
                    None,
                ),
            }
            for result in results
        ],
    }


# ============================================================
# PLAN
# ============================================================

@router.post("/{case_id}/plan")
def plan_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    if (
        not case.issue
        or not case.recommended_action
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Case must be analyzed "
                "before planning."
            ),
        )

    decision = CaseDecision(
        issue=case.issue,
        recommended_action=(
            case.recommended_action
        ),
        priority=(
            case.priority
            or "MEDIUM"
        ),
        reason=(
            case.decision_reason
            or ""
        ),
    )

    try:

        plan = plan_case(
            db=db,
            case=case,
            decision=decision,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "approval_required": (
                case.approval_required
            ),
        },

        "plan": {
            "summary": plan.summary,
            "steps": plan.steps,
            "approval_required": (
                plan.approval_required
            ),
        },
    }


# ============================================================
# SYNTHESIS
#
# RESEARCH
# ->
# EVIDENCE
# ->
# DECISION
# ->
# PLAN
# ============================================================

@router.post("/{case_id}/synthesize")
def synthesize_case_endpoint(
    case_id: int,
    run_research: bool = False,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    # ========================================================
    # OPTIONAL RESEARCH
    # ========================================================

    if run_research:

        existing = (
            db.query(CaseResearch)
            .filter(
                CaseResearch.case_id
                == case.id
            )
            .count()
        )

        if existing == 0:

            record_activity(
                db=db,
                case_id=case.id,
                event_type=(
                    "SYNTHESIS_ORCHESTRATION"
                ),
                message=(
                    "Synthesis requested with "
                    "research; invoking research."
                ),
            )

            try:

                research_case(
                    db=db,
                    case=case,
                )

            except ValueError as exc:

                raise HTTPException(
                    status_code=400,
                    detail=str(exc),
                ) from exc

    # ========================================================
    # SYNTHESIS
    # ========================================================

    try:

        result = synthesize_evidence_and_plan(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "issue": case.issue,
            "recommended_action": (
                case.recommended_action
            ),
            "priority": case.priority,
            "decision_reason": (
                case.decision_reason
            ),
            "plan_summary": (
                case.plan_summary
            ),
            "plan_steps": (
                case.plan_steps
            ),
            "approval_required": (
                case.approval_required
            ),
        },

        "decision": {
            "issue": result.get(
                "issue"
            ),
            "recommended_action": result.get(
                "recommended_action"
            ),
            "priority": result.get(
                "priority"
            ),
            "reason": result.get(
                "decision_reason"
            ),
            "confidence": result.get(
                "confidence"
            ),
            "evidence_strength": result.get(
                "evidence_strength"
            ),
        },

        "plan": {
            "summary": result.get(
                "plan_summary"
            ),
            "steps": result.get(
                "plan_steps"
            ),
            "approval_required": result.get(
                "approval_required"
            ),
        },

        "evidence": result.get(
            "evidence"
        ),

        "stance": result.get(
            "stance"
        ),
    }


# ============================================================
# END-TO-END PROCESS ORCHESTRATION
# ============================================================


@router.post("/{case_id}/process")
def process_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PROCESS_STARTED",
        message="ONIT started end-to-end case processing.",
    )

    # 1) Analyze (includes evidence sufficiency check)
    try:
        decision = analyze_case(db=db, case=case)
    except Exception as exc:
        # analyze_case already records failures; surface as 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    db.refresh(case)

    # If analysis determined more information is required, stop here.
    if case.status == CaseStatus.NEEDS_INFORMATION:

        missing = None
        try:
            missing = _json.loads(case.missing_information or "{}")
        except Exception:
            missing = {"needs_information": True, "missing_information": []}

        record_activity(
            db=db,
            case_id=case.id,
            event_type="PROCESS_HALTED_NEEDS_INFORMATION",
            message="ONIT halted processing because additional information is required.",
        )

        return {
            "status": "ok",
            "case": {
                "id": case.id,
                "status": case.status,
                "missing_information": missing.get("missing_information") if isinstance(missing, dict) else [],
            },
        }

    # 2) Research (question-driven). Only run if research hasn't already been done.
    existing = (
        db.query(CaseResearch)
        .filter(CaseResearch.case_id == case.id)
        .count()
    )

    if existing == 0:
        try:
            research_case(db=db, case=case)
        except ValueError as exc:
            # Research failed (e.g., missing API key or external error)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.refresh(case)

    # 3) Synthesize evidence into decision and plan
    try:
        result = synthesize_evidence_and_plan(db=db, case=case)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_activity(
        db=db,
        case_id=case.id,
        event_type="PROCESS_COMPLETED",
        message="ONIT completed end-to-end processing for the case.",
    )

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "issue": case.issue,
            "recommended_action": case.recommended_action,
            "priority": case.priority,
        },

        "decision": {
            "issue": result.get("issue"),
            "recommended_action": result.get("recommended_action"),
            "priority": result.get("priority"),
            "reason": result.get("decision_reason"),
        },

        "plan": {
            "summary": result.get("plan_summary"),
            "steps": result.get("plan_steps"),
            "approval_required": result.get("approval_required"),
        },

        "evidence": result.get("evidence"),
    }


# ============================================================
# REQUEST APPROVAL
# ============================================================

@router.post("/{case_id}/request-approval")
def request_case_approval_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:

        case = request_case_approval(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "recommended_action": (
                case.recommended_action
            ),
            "approval_required": (
                case.approval_required
            ),
        },
    }


# ============================================================
# APPROVE
# ============================================================

@router.post("/{case_id}/approve")
def approve_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:

        case = approve_case(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,
            "status": case.status,
            "recommended_action": (
                case.recommended_action
            ),
            "approval_required": (
                case.approval_required
            ),
        },
    }


# ============================================================
# EXECUTE
# ============================================================

@router.post("/{case_id}/execute")
def execute_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:

        case = execute_case(
            db=db,
            case=case,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",

        "case": {
            "id": case.id,

            "status": case.status,

            "recommended_action": (
                case.recommended_action
            ),

            "approval_required": (
                case.approval_required
            ),

            "plan_summary": (
                case.plan_summary
            ),

            "plan_steps": (
                case.plan_steps
            ),
        },
    }


# ============================================================
# RESPONSE
# ============================================================

class RecordResponseRequest(BaseModel):
    response_type: str
    message: str
    resolved: bool = False


@router.post("/{case_id}/response")
def record_response_endpoint(
    case_id: int,
    request: RecordResponseRequest,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:
        response = record_case_response(
            db=db,
            case=case,
            response_type=request.response_type,
            message=request.message,
            resolved=request.resolved,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "response": {
            "id": response.id,
            "case_id": response.case_id,
            "response_type": response.response_type,
            "message": response.message,
            "resolved": response.resolved,
            "created_at": response.created_at,
        },
        "case": {
            "id": case.id,
            "status": case.status,
        },
    }


    # ========================================================
    # 1. FIND CASE
    # ========================================================

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    # ========================================================
    # 2. RECORD RESPONSE
    # ========================================================

    try:

        response = record_case_response(
            db=db,
            case=case,
            response_type=request.response_type,
            message=request.message,
            resolved=request.resolved,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ========================================================
    # 3. REFRESH CASE
    #
    # record_case_response() is responsible for changing
    # the case status when the response resolves the case.
    # Refresh ensures the returned status is the persisted one.
    # ========================================================

    db.refresh(case)
    db.refresh(response)

    # ========================================================
    # 4. RESPONSE
    # ========================================================

    return {
        "status": "ok",

        "response": {
            "id": response.id,
            "case_id": response.case_id,
            "response_type": response.response_type,
            "message": response.message,
            "resolved": response.resolved,
            "created_at": response.created_at,
        },

        "case": {
            "id": case.id,
            "status": case.status,
        },
    }
    
# ============================================================
# FOLLOW-UP
# ============================================================

@router.post("/{case_id}/follow-up")
def send_follow_up_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    try:
        case = send_case_follow_up(
            db=db,
            case=case,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "case": {
            "id": case.id,
            "status": case.status,
        },
    }


# ============================================================
# GET SINGLE CASE
#
# KEEP THIS LAST
# ============================================================

@router.get("/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
):

    case = db.get(
        Case,
        case_id,
    )

    if case is None:

        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    responses = (
        db.query(CaseResponse)
        .filter(
            CaseResponse.case_id == case.id
        )
        .order_by(
            CaseResponse.created_at.asc()
        )
        .all()
    )

    research_items = (
        db.query(CaseResearch)
        .filter(
            CaseResearch.case_id == case.id
        )
        .order_by(
            CaseResearch.created_at.asc()
        )
        .all()
    )

    evidence_items = (
        db.query(CaseEvidence)
        .filter(
            CaseEvidence.case_id == case.id
        )
        .order_by(
            CaseEvidence.created_at.asc(),
            CaseEvidence.id.asc(),
        )
        .all()
    )

    activities = (
        db.query(CaseActivity)
        .filter(
            CaseActivity.case_id == case.id
        )
        .order_by(
            CaseActivity.created_at.asc(),
            CaseActivity.id.asc(),
        )
        .all()
    )

    evidence_strength = "insufficient"
    confidence = 0
    stance = {
        "supporting": 0,
        "conflicting": 0,
        "uncertain": 0,
        "total": 0,
    }

    if research_items:
        high = sum(
            1
            for item in research_items
            if (item.relevance or "").lower() == "high"
        )

        if high >= 2:
            evidence_strength = "strong"
        elif high >= 1 or len(research_items) >= 3:
            evidence_strength = "moderate"

        confidence = 50 + min(high * 10, 30)

        authoritative = sum(
            1
            for item in research_items
            if item.url and ".gov" in item.url.lower()
        )
        confidence += min(authoritative * 5, 10)

        if len(research_items) >= 5:
            confidence += 5
        elif len(research_items) >= 3:
            confidence += 3

        confidence = max(0, min(100, confidence))

        supporting = 0
        uncertain = 0
        for item in research_items:
            url = (item.url or "").lower()
            source = (item.source or "").lower()
            relevance = (item.relevance or "").lower()

            if relevance == "high":
                if ".gov" in url or "official" in source:
                    supporting += 1
                else:
                    uncertain += 1
            else:
                uncertain += 1

        stance = {
            "supporting": supporting,
            "conflicting": 0,
            "uncertain": uncertain,
            "total": len(research_items),
        }

    return {
        "status": "ok",

        "case": {
            "id": case.id,

            "title": case.title,

            "description": case.description,

            "passenger": case.passenger,

            "booking_reference": (
                case.booking_reference
            ),

            "organization": (
                case.organization
            ),

            "airline": case.airline,
            "flight_number": getattr(case, "flight_number", None),

            "cancellation_date": (
                case.cancellation_date
            ),

            "amount": case.amount,
            "amount_value": getattr(case, "amount_value", None),
            "amount_currency": getattr(case, "amount_currency", None),

            "currency": case.currency,

            "refund_received": (
                case.refund_received
            ),

            "requested_resolution": (
                case.requested_resolution
            ),

            "supporting_facts": (
                (lambda v: (json.loads(v) if v else None))(
                    case.supporting_facts
                )
                if isinstance(getattr(case, "supporting_facts", None), str)
                else getattr(case, "supporting_facts", None)
            ),

            "issue": case.issue,

            "recommended_action": (
                case.recommended_action
            ),

            "priority": case.priority,

            "decision_reason": (
                case.decision_reason
            ),

            "plan_summary": (
                case.plan_summary
            ),

            "plan_steps": (
                (lambda v: (json.loads(v) if v else None))(
                    case.plan_steps
                )
                if isinstance(getattr(case, "plan_steps", None), str)
                else getattr(case, "plan_steps", None)
            ),

            "approval_required": (
                case.approval_required
            ),

            "status": case.status,

            "evidence_strength": evidence_strength,

            "confidence": confidence,

            "stance": stance,

            "created_at": (
                case.created_at
            ),

            "updated_at": (
                case.updated_at
            ),
        },

        "evidence": [
            {
                "id": item.id,
                "filename": item.filename,
                "evidence_type": item.evidence_type,
                "mimetype": item.mimetype,
                "extraction_status": item.extraction_status,
                "original_text": item.original_text,
                "extracted_text": item.extracted_text,
                "extracted_facts": (
                    (lambda v: json.loads(v) if v else {})(
                        item.extracted_facts
                    )
                    if isinstance(getattr(item, "extracted_facts", None), str)
                    else getattr(item, "extracted_facts", None) or {}
                ),
                "created_at": item.created_at,
            }
            for item in evidence_items
        ],

        "research": [
            {
                "id": item.id,
                "source": item.source,
                "title": item.title,
                "summary": item.summary,
                "relevance": item.relevance,
                "url": getattr(item, "url", None),
                "created_at": item.created_at,
            }
            for item in research_items
        ],

        "activity": [
            {
                "id": activity.id,
                "event_type": activity.event_type,
                "message": activity.message,
                "created_at": activity.created_at,
            }
            for activity in activities
        ],

        "responses": [
            {
                "id": response.id,
                "case_id": response.case_id,
                "response_type": response.response_type,
                "message": response.message,
                "resolved": response.resolved,
                "created_at": response.created_at,
            }
            for response in responses
        ],
    }