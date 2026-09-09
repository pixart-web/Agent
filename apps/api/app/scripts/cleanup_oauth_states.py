from app.db.session import SessionLocal
from app.services.oauth_state_cleanup import cleanup_oauth_states


def main() -> None:
    with SessionLocal() as session:
        deleted = cleanup_oauth_states(session)

    print(f"OAuth state cleanup complete: deleted={deleted}")


if __name__ == "__main__":
    main()
