import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-only-auth-secret-with-at-least-32-characters",
)
os.environ.setdefault("AUTH_REQUIRE_EMAIL_VERIFICATION", "false")

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Agent, RefreshToken, User
from app.services.rate_limiter import (
    RateLimitDecision,
    RateLimiter,
    get_rate_limiter,
)

_ = (Agent, RefreshToken, User)


class AllowAllRateLimiter(RateLimiter):
    def check(self, endpoint: str, ip_address: str) -> RateLimitDecision:
        return RateLimitDecision(allowed=True)


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()


def _test_engine():
    """SQLite in memory by default; a disposable PostgreSQL database when TEST_DATABASE_URL is
    set (the schema is dropped after every test, so the name must say it is a test database)."""
    if not TEST_DATABASE_URL:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # SQLite ignores foreign keys unless asked; PostgreSQL always enforces them.
        event.listen(
            engine, "connect", lambda conn, _record: conn.execute("PRAGMA foreign_keys=ON")
        )
        return engine
    url = make_url(TEST_DATABASE_URL)
    if "test" not in (url.database or "").lower():
        raise RuntimeError("TEST_DATABASE_URL must name a disposable *test* database")
    return create_engine(url, pool_pre_ping=True)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = _test_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    with testing_session() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rate_limiter] = lambda: AllowAllRateLimiter()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
