import os
import tempfile
from pathlib import Path

import pytest

test_database = Path(tempfile.gettempdir()) / "astrolive-feature-test.db"
test_database.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_database.as_posix()}"
os.environ["ASTROLOGY_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from app.core.database import engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    test_database.unlink(missing_ok=True)
