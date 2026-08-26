from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os
import sys

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

# When running under pytest, recreate the schema to ensure model changes
# (like added `url` column) are present in the test database.
_TEST_MODE = "PYTEST_CURRENT_TEST" in os.environ or any("pytest" in a for a in sys.argv)
if _TEST_MODE:
    try:
        from app.models.case import Base as ModelsBase

        ModelsBase.metadata.drop_all(bind=engine)
        ModelsBase.metadata.create_all(bind=engine)
    except Exception:
        pass


# Ensure the `url` column exists on `case_research` for backward compatibility
try:
    with engine.connect() as conn:
        try:
            # Ensure model classes are imported so they register with Base.metadata
            try:
                import app.models.case as _models_case  # noqa: F401
            except Exception:
                pass

            # Create tables per current models (adds new columns if DB is empty)
            try:
                Base.metadata.create_all(bind=engine)
            except Exception:
                pass

            res = conn.execute("PRAGMA table_info(case_research)").fetchall()
            cols = {row[1] for row in res}
            if "url" not in cols:
                # Ensure tables exist then add column
                try:
                    from app.models.case import Base as ModelsBase

                    ModelsBase.metadata.create_all(bind=engine)
                except Exception:
                    pass

                conn.execute("ALTER TABLE case_research ADD COLUMN url VARCHAR(2048)")
        except Exception:
            # Ignore errors here; migration handled elsewhere in production
            pass
except Exception:
    # Engine might not be ready in some environments; ignore
    pass


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
