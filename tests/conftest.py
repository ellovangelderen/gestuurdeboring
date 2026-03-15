"""Shared fixtures voor alle testcases."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Zet test-omgeving vóór imports van app modules
os.environ.setdefault("ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_hdd.db")
os.environ.setdefault("USER_MARTIEN_PASSWORD", "test-martien")
os.environ.setdefault("USER_VISSER_PASSWORD", "test-visser")
os.environ.setdefault("USER_TEST_PASSWORD", "test123")

from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

# In-memory SQLite met StaticPool — alle connecties delen dezelfde DB instantie
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Importeer alle modellen zodat tabellen bekend zijn
import app.core.models  # noqa: F401
import app.project.models  # noqa: F401
import app.rules.models  # noqa: F401
# KLICLeiding is gedefinieerd in app.project.models — al geïmporteerd hierboven


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# Seed workspace voor tests die het nodig hebben
@pytest.fixture
def workspace(db):
    from app.core.models import Workspace
    ws = Workspace(id="gbt-workspace-001", naam="GestuurdeBoringTekening", slug="gbt")
    db.add(ws)
    db.commit()
    return ws


AUTH = ("martien", "test-martien")
