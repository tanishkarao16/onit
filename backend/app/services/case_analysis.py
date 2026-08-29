import json

from sqlalchemy.orm import Session

from app.models.case import Case as CaseModel, CaseStatus
from app.services.case_activity import record_activity
from app.services.case_decision import (
    CaseDecision,
    decide_case,
)
from app.services.case_parser import Case as ParsedCase


# ============================================================
# ANALYZE CASE
# ============================================================

def analyze_case(
    db: Session,
    case: CaseModel,
) -> CaseDecision:

    # --------------------------------------------------------
    # START ANALYSIS
    # --------------------------------------------------------

    case.status = CaseStatus.ANALYZING
    db.commit()

    record_activity(
        db=db,
        case_id=case.id,
        event_type="ANALYSIS_STARTED",
        message="ONIT started analyzing the case.",
    )

    try:

        # ====================================================
        # SUPPORTING FACTS
        # ====================================================

        supporting_facts = []

        if case.supporting_facts:

            try:

                loaded = json.loads(
                    case.supporting_facts
                )

                if isinstance(
                    loaded,
                    list,
                ):
                    supporting_facts = loaded

                elif isinstance(
                    loaded,
                    str,
                ):
                    supporting_facts = [
                        loaded
                    ]

            except (
                TypeError,
                json.JSONDecodeError,
            ):

                supporting_facts = [
                    str(
                        case.supporting_facts
                    )
                ]

        # ====================================================
        # NORMALIZE CURRENCY / AMOUNT
        # ====================================================

        amount_value = getattr(
            case,
            "amount_value",
            None,
        )

        amount_currency = getattr(
            case,
            "amount_currency",
            None,
        )

        if not amount_value:
            amount_value = case.amount

        if not amount_currency:
            amount_currency = (
                case.currency
            )

        # ====================================================
        # BUILD PARSED CASE
        # ====================================================

        parsed_case = ParsedCase(
            passenger=case.passenger,

            booking_reference=(
                case.booking_reference
            ),

            airline=case.airline,

            cancellation_date=(
                case.cancellation_date
            ),

            flight_number=getattr(
                case,
                "flight_number",
                None,
            ),

            amount=case.amount,

            amount_value=amount_value,

            amount_currency=amount_currency,

            refund_received=(
                case.refund_received
            ),

            requested_resolution=(
                case.requested_resolution
            ),

            supporting_facts=supporting_facts,
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # ParsedCase may not contain description.
        # Attach it dynamically so the decision engine
        # can analyze manually-created cases too.
        # ----------------------------------------------------

        parsed_case.description = (
            case.description or ""
        )

        # ====================================================
        # DECISION
        # ====================================================

        decision = decide_case(
            parsed_case
        )

        # ====================================================
        # SAVE DECISION
        # ====================================================

        case.issue = (
            decision.issue
        )

        case.recommended_action = (
            decision.recommended_action
        )

        case.priority = (
            decision.priority
        )

        case.decision_reason = (
            decision.reason
        )

        case.status = (
            CaseStatus.EVIDENCE_READY
        )

        db.commit()
        db.refresh(case)

        # ====================================================
        # ACTIVITY
        # ====================================================

        record_activity(
            db=db,
            case_id=case.id,
            event_type="ANALYSIS_COMPLETED",
            message=(
                f"ONIT identified: "
                f"{decision.issue}. "
                f"Recommended action: "
                f"{decision.recommended_action}."
            ),
        )

        return decision

    # ========================================================
    # FAILURE
    # ========================================================

    except Exception:

        case.status = (
            CaseStatus.CREATED
        )

        db.commit()

        record_activity(
            db=db,
            case_id=case.id,
            event_type="ANALYSIS_FAILED",
            message=(
                "ONIT analysis failed."
            ),
        )

        raise