from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.refresh_token_cleanup import cleanup_refresh_tokens


def main() -> None:
    settings = get_settings()
    with SessionLocal() as session:
        deleted = cleanup_refresh_tokens(
            session,
            retention_days=settings.auth_cleanup_retention_days,
        )

    print(f"Refresh token cleanup complete: deleted={deleted}")


if __name__ == "__main__":
    main()
