from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import Base, engine, get_db
from app.integrations.nutrient import NutrientError, parse_document
from app.models.case import Case, CaseActivity, CaseResearch, CaseStatus
from app.services.case_analysis import analyze_case
from app.services.case_approval import request_case_approval
from app.services.case_decision import CaseDecision
from app.services.case_parser import parse_case
from app.services.case_persistence import persist_parsed_case
from app.services.case_planning import plan_case
from app.services.case_research import research_case
from app.services.evidence_to_decision import synthesize_evidence_and_plan
from app.services.case_research import research_case
from app.models.case import CaseResearch
from app.services.case_activity import record_activity


Base.metadata.create_all(bind=engine)

# Ensure `url` column exists on `case_research` table when model adds it.
with engine.connect() as conn:
    try:
        res = conn.execute(
            "PRAGMA table_info(case_research)"
        ).fetchall()
        cols = {row[1] for row in res}
        if "url" not in cols:
            conn.execute("ALTER TABLE case_research ADD COLUMN url VARCHAR(2048)")
    except Exception:
        # Non-fatal: leave existing schema as-is if pragma/alter fail
        pass

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
def list_cases(
    db: Session = Depends(get_db),
):
    cases = (
        db.query(Case)
        .order_by(Case.created_at.desc())
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


@router.get("/{case_id}/activity")
def get_case_activity(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    activities = (
        db.query(CaseActivity)
        .filter(CaseActivity.case_id == case_id)
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


@router.get("/{case_id}/research")
def get_case_research(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    research = (
        db.query(CaseResearch)
        .filter(CaseResearch.case_id == case_id)
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
                "created_at": item.created_at,
            }
            for item in research
        ],
    }


@router.post("/{case_id}/analyze")
def analyze_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

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
            "recommended_action": case.recommended_action,
            "priority": case.priority,
            "decision_reason": case.decision_reason,
        },
        "decision": {
            "issue": decision.issue,
            "recommended_action": decision.recommended_action,
            "priority": decision.priority,
            "reason": decision.reason,
        },
    }


@router.post("/{case_id}/research")
def research_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

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
            }
            for result in results
        ],
    }


@router.post("/{case_id}/plan")
def plan_case_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    if not case.issue or not case.recommended_action:
        raise HTTPException(
            status_code=400,
            detail="Case must be analyzed before planning.",
        )

    decision = CaseDecision(
        issue=case.issue,
        recommended_action=case.recommended_action,
        priority=case.priority or "MEDIUM",
        reason=case.decision_reason or "",
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
            "approval_required": case.approval_required,
        },
        "plan": {
            "summary": plan.summary,
            "steps": plan.steps,
            "approval_required": plan.approval_required,
        },
    }



@router.post("/{case_id}/synthesize")
def synthesize_case_endpoint(
    case_id: int,
    run_research: bool = False,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    # Optionally run research first when requested and no persisted evidence exists
    if run_research:
        # check for existing persisted research
        existing = (
            db.query(CaseResearch)
            .filter(CaseResearch.case_id == case.id)
            .count()
        )
        if existing == 0:
            # record orchestration activity
            record_activity(
                db=db,
                case_id=case.id,
                event_type="SYNTHESIS_ORCHESTRATION",
                message="Synthesis requested with research; invoking research.",
            )

            try:
                research_case(db=db, case=case)
            except ValueError as exc:
                # propagate as HTTP 400 with the research error message
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = synthesize_evidence_and_plan(db=db, case=case)
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
            "recommended_action": case.recommended_action,
            "priority": case.priority,
            "decision_reason": case.decision_reason,
            "plan_summary": case.plan_summary,
            "plan_steps": case.plan_steps,
            "approval_required": case.approval_required,
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


@router.post("/{case_id}/request-approval")
def request_case_approval_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

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
            "recommended_action": case.recommended_action,
            "approval_required": case.approval_required,
        },
    }


@router.get("/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    return {
        "status": "ok",
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "passenger": case.passenger,
            "booking_reference": case.booking_reference,
            "organization": case.organization,
            "airline": case.airline,
            "cancellation_date": case.cancellation_date,
            "amount": case.amount,
            "currency": case.currency,
            "refund_received": case.refund_received,
            "requested_resolution": case.requested_resolution,
            "supporting_facts": case.supporting_facts,
            "issue": case.issue,
            "recommended_action": case.recommended_action,
            "priority": case.priority,
            "decision_reason": case.decision_reason,
            "plan_summary": case.plan_summary,
            "plan_steps": case.plan_steps,
            "approval_required": case.approval_required,
            "status": case.status,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
        },
    }


@router.post("/parse")
async def parse_case_document(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required.",
        )

    suffix = Path(file.filename).suffix or ".bin"

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
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
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except NutrientError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@router.post("/parse-and-create")
async def parse_and_create_case(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required.",
        )

    suffix = Path(file.filename).suffix or ".bin"

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
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
        case = persist_parsed_case(
            db,
            parsed_case,
        )

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
                "supporting_facts": case.supporting_facts,
                "status": case.status,
            },
        }

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