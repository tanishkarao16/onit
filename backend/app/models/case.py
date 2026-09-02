from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ============================================================
# CASE STATUS
# ============================================================

class CaseStatus(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    EVIDENCE_READY = "EVIDENCE_READY"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    RESEARCHING = "RESEARCHING"
    PLANNING = "PLANNING"
    ACTION_READY = "ACTION_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# ============================================================
# CASE
# ============================================================

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # --------------------------------------------------------
    # IDENTITY / CASE FACTS
    # --------------------------------------------------------

    passenger: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    booking_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    organization: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    airline: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    flight_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    cancellation_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # --------------------------------------------------------
    # MONEY
    # --------------------------------------------------------

    amount: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    amount_value: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    amount_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # --------------------------------------------------------
    # REFUND / REQUEST
    # --------------------------------------------------------

    refund_received: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    requested_resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    supporting_facts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    issue: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommended_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # MISSING INFORMATION (structured JSON)
    # --------------------------------------------------------

    missing_information: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # PLAN
    # --------------------------------------------------------

    plan_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    plan_steps: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    approval_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status: Mapped[CaseStatus] = mapped_column(
        SQLEnum(CaseStatus),
        default=CaseStatus.CREATED,
        nullable=False,
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# CASE ACTIVITY
# ============================================================

class CaseActivity(Base):
    __tablename__ = "case_activities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    case_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# CASE RESEARCH
# ============================================================

class CaseResearch(Base):
    __tablename__ = "case_research"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    case_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    relevance: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# CASE EVIDENCE
# ============================================================

class CaseEvidence(Base):
    __tablename__ = "case_evidence"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    case_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    mimetype: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    original_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    extracted_facts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

# ============================================================
# CASE RESPONSE
# ============================================================

class CaseResponse(Base):
    __tablename__ = "case_responses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    case_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    response_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
