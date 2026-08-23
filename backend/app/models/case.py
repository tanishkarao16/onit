from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class CaseStatus(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    EVIDENCE_READY = "EVIDENCE_READY"
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


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    status: Mapped[CaseStatus] = mapped_column(
        SQLEnum(CaseStatus),
        default=CaseStatus.CREATED,
        nullable=False,
    )

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
