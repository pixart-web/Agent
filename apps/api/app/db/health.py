from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine


def database_is_healthy() -> bool:
    """Check PostgreSQL without exposing connection details."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def redis_is_healthy() -> bool:
    """Check Redis with short timeouts and close the client afterwards."""
    settings = get_settings()
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.service_connect_timeout_seconds,
        socket_timeout=settings.service_connect_timeout_seconds,
    )

    try:
        return bool(client.ping())
    except RedisError:
        return False
    finally:
        client.close()
