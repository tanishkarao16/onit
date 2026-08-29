from dataclasses import dataclass

from app.services.case_parser import Case


# ============================================================
# DECISION OBJECT
# ============================================================

@dataclass
class CaseDecision:
    issue: str
    recommended_action: str
    priority: str
    reason: str


# ============================================================
# HELPERS
# ============================================================

def _text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _lower(value) -> str:
    return _text(value).lower()


def _contains_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


# ============================================================
# CASE DECISION ENGINE
# ============================================================

def decide_case(case: Case) -> CaseDecision:

    # --------------------------------------------------------
    # COLLECT ALL AVAILABLE INFORMATION
    # --------------------------------------------------------

    description = _lower(
        getattr(case, "description", None)
    )

    passenger = _text(
        getattr(case, "passenger", None)
    )

    booking_reference = _text(
        getattr(case, "booking_reference", None)
    )

    airline = _text(
        getattr(case, "airline", None)
    )

    flight_number = _text(
        getattr(case, "flight_number", None)
    )

    cancellation_date = _text(
        getattr(case, "cancellation_date", None)
    )

    amount = _text(
        getattr(case, "amount", None)
    )

    refund_received = getattr(
        case,
        "refund_received",
        None,
    )

    requested_resolution = _text(
        getattr(case, "requested_resolution", None)
    )

    supporting_facts = getattr(
        case,
        "supporting_facts",
        [],
    )

    # --------------------------------------------------------
    # BUILD SEARCHABLE CASE TEXT
    # --------------------------------------------------------

    searchable_text = " ".join(
        [
            description,
            passenger.lower(),
            booking_reference.lower(),
            airline.lower(),
            flight_number.lower(),
            cancellation_date.lower(),
            amount.lower(),
            requested_resolution.lower(),
            " ".join(
                str(x).lower()
                for x in supporting_facts
                if x
            ),
        ]
    )

    # ========================================================
    # FLIGHT / AIRLINE REFUND
    # ========================================================

    cancellation_keywords = [
        "cancelled",
        "canceled",
        "flight cancellation",
        "flight was cancelled",
        "flight was canceled",
        "airline cancelled",
        "airline canceled",
    ]

    refund_keywords = [
        "refund",
        "refunded",
        "money back",
        "reimbursement",
        "reimburse",
    ]

    flight_keywords = [
        "flight",
        "airline",
        "airways",
        "airway",
        "airport",
        "booking",
        "passenger",
    ]

    is_cancellation = _contains_any(
        searchable_text,
        cancellation_keywords,
    )

    is_refund_issue = _contains_any(
        searchable_text,
        refund_keywords,
    )

    is_flight_case = _contains_any(
        searchable_text,
        flight_keywords,
    )

    if (
        is_cancellation
        and is_refund_issue
        and is_flight_case
    ):

        if refund_received is True:

            return CaseDecision(
                issue="Flight cancellation refund",
                recommended_action=(
                    "Verify the refund amount and "
                    "confirm that the passenger received "
                    "the expected refund."
                ),
                priority="medium",
                reason=(
                    "The case concerns a cancelled flight "
                    "and indicates that a refund was received. "
                    "The next step is to verify the refund."
                ),
            )

        return CaseDecision(
            issue="Flight cancellation refund not received",
            recommended_action=(
                "Research the applicable airline refund "
                "policy and passenger rights, verify "
                "eligibility, and prepare a refund request."
            ),
            priority="high",
            reason=(
                "The available case information indicates "
                "that a flight was cancelled and the passenger "
                "has not received the expected refund."
            ),
        )

    # ========================================================
    # GENERIC REFUND
    # ========================================================

    if is_refund_issue:

        return CaseDecision(
            issue="Refund request",
            recommended_action=(
                "Verify the refund eligibility and "
                "research the applicable refund policy "
                "before preparing the next action."
            ),
            priority="medium",
            reason=(
                "The case contains a refund-related request, "
                "but the available information does not "
                "identify a more specific automated workflow."
            ),
        )

    # ========================================================
    # CANCELLATION WITHOUT REFUND
    # ========================================================

    if is_cancellation:

        return CaseDecision(
            issue="Cancellation-related case",
            recommended_action=(
                "Review the cancellation circumstances "
                "and determine the applicable remedy."
            ),
            priority="medium",
            reason=(
                "The case describes a cancellation, "
                "but does not contain enough information "
                "to identify a specific remedy automatically."
            ),
        )

    # ========================================================
    # PAYMENT / CHARGE
    # ========================================================

    payment_keywords = [
        "payment",
        "charged",
        "charge",
        "credit card",
        "debit card",
        "transaction",
        "billing",
    ]

    if _contains_any(
        searchable_text,
        payment_keywords,
    ):

        return CaseDecision(
            issue="Payment or billing issue",
            recommended_action=(
                "Review the transaction details, "
                "verify the charge, and determine "
                "the appropriate resolution."
            ),
            priority="medium",
            reason=(
                "The case contains payment or billing "
                "information requiring verification."
            ),
        )

    # ========================================================
    # DELIVERY / PURCHASE
    # ========================================================

    delivery_keywords = [
        "delivery",
        "delivered",
        "package",
        "parcel",
        "shipment",
        "order",
    ]

    if _contains_any(
        searchable_text,
        delivery_keywords,
    ):

        return CaseDecision(
            issue="Delivery or order issue",
            recommended_action=(
                "Verify the order and delivery status "
                "and determine the appropriate next action."
            ),
            priority="medium",
            reason=(
                "The case contains delivery or order-related "
                "information."
            ),
        )

    # ========================================================
    # UNKNOWN / HUMAN REVIEW
    # ========================================================

    return CaseDecision(
        issue="Case requires review",
        recommended_action=(
            "Review the case and determine the "
            "appropriate next action."
        ),
        priority="medium",
        reason=(
            "The available case information does not "
            "match a known automated workflow."
        ),
    )