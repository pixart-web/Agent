import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-only-auth-secret-with-at-least-32-characters",
)

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


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
