from app.db.session import SessionLocal
from app.services.agent_service import seed_initial_agents


def main() -> None:
    with SessionLocal() as session:
        result = seed_initial_agents(session)

    print(f"Agent seed complete: created={result.created}, updated={result.updated}")


if __name__ == "__main__":
    main()
