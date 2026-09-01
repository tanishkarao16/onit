from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = "sqlite:///./onit.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# ============================================================
# BASE MODEL
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create all database tables defined by SQLAlchemy models.

    Importing the models here ensures SQLAlchemy knows about
    every table before create_all() runs.
    """
    from app.models.case import (
        Case,
        CaseActivity,
        CaseResearch,
        CaseEvidence,
        CaseResponse,
    )

    Base.metadata.create_all(bind=engine)


# ============================================================
# DATABASE SESSION
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()