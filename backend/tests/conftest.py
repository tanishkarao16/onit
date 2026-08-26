import pytest

from app.db import database
from app.models.case import Base as ModelsBase


def pytest_sessionstart(session):
    # Ensure test DB schema matches current models (adds `url` column)
    try:
        ModelsBase.metadata.drop_all(bind=database.engine)
    except Exception:
        pass
    ModelsBase.metadata.create_all(bind=database.engine)
