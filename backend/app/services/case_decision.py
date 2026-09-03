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
    text = _lower(text)

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


def _facts_to_text(facts) -> str:
    if facts is None:
        return ""

    if isinstance(facts, list):
        return " ".join(
            _text(item)
            for item in facts
            if item
        )

    return _text(facts)


# ============================================================
# CASE DECISION ENGINE
# ============================================================

def decide_case(case: Case) -> CaseDecision:

    # --------------------------------------------------------
    # COLLECT AVAILABLE INFORMATION
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

    facts_text = _facts_to_text(
        supporting_facts
    ).lower()

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
            facts_text,
        ]
    )

    # ========================================================
    # DOMAIN DETECTION + DECISION
    # ========================================================

    # Domain-specific keyword groups
    domains = {
        "insurance": [
            "insurance",
            "claim",
            "policy",
            "denied",
            "denial",
            "claimant",
            "policy number",
            "claim number",
        ],
        "flight": [
            "flight",
            "airline",
            "airways",
            "booking",
            "passenger",
            "cancellation",
        ],
        "bank": [
            "bank",
            "transaction",
            "dispute",
            "account",
            "charge",
        ],
        "rental": [
            "tenancy",
            "deposit",
            "landlord",
            "rental",
            "lease",
        ],
    }

    def detect_domain(text: str) -> str | None:
        for name, keys in domains.items():
            if _contains_any(text, keys):
                return name
        return None

    domain = detect_domain(searchable_text)

    # Insurance claim handling
    if domain == "insurance":
        # Determine if denial present
        denied = _contains_any(searchable_text, ["denied", "denial", "was denied", "not covered"]) or ("denied" in description)

        issue_text = (
            requested_resolution
            or description
            or supporting_facts
            or "Insurance claim"
        )

        recommended = (
            "Review the policy terms, the denial reason, and prepare a reconsideration or escalation package. "
            "Include policy references and claim identifiers when contacting the insurer."
        )

        priority = "medium"

        reason = (
            "The case contains insurance claim indicators"
            + (" and appears to be a denial." if denied else ".")
        )

        return CaseDecision(
            issue=(
                "Insurance claim denial" if denied else "Insurance claim"
            ),
            recommended_action=recommended,
            priority=priority,
            reason=reason,
        )

    # Bank/payment related cases
    if domain == "bank":
        return CaseDecision(
            issue="Payment or bank dispute",
            recommended_action=(
                "Review the transaction and account details, gather bank statements, "
                "and prepare a dispute or chargeback request if appropriate."
            ),
            priority="medium",
            reason=(
                "The case contains banking or payment-related terms requiring financial dispute handling."
            ),
        )

    # Flight-specific cases (keep existing behavior but only when flight indicators are strong)
    if domain == "flight":
        # reuse previous cancellation/refund heuristics but scoped to flight domain
        cancellation_keywords = [
            "cancelled",
            "canceled",
            "cancellation",
        ]

        refund_keywords = [
            "refund",
            "refunded",
            "money back",
            "reimbursement",
            "reimburse",
        ]

        is_cancellation = (
            _contains_any(searchable_text, cancellation_keywords)
            or bool(cancellation_date)
        )

        is_refund_issue = _contains_any(searchable_text, refund_keywords)

        if is_cancellation and is_refund_issue:
            if refund_received is True:
                return CaseDecision(
                    issue="Flight cancellation refund",
                    recommended_action=(
                        "Verify the refund amount and confirm that the passenger received the expected refund."
                    ),
                    priority="medium",
                    reason=(
                        "The case concerns a cancelled flight and indicates that a refund was received."
                    ),
                )

            amount_text = f" for {amount}" if amount else ""

            return CaseDecision(
                issue="Cancelled flight with refund not received",
                recommended_action=(
                    "Verify the passenger's refund eligibility, contact the airline to request the applicable refund, "
                    "and follow up until a response is received."
                ),
                priority="high",
                reason=(
                    "The available case information indicates that a flight was cancelled and the passenger has not received the expected refund"
                    f"{amount_text}."
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
