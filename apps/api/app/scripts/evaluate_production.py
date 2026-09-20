import argparse

from app.db.session import SessionLocal
from app.operations.evaluation import evaluate_production


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only production readiness evaluation")
    parser.add_argument("--window-days", type=int, default=30, choices=range(1, 366))
    args = parser.parse_args()
    with SessionLocal() as session:
        report = evaluate_production(session, window_days=args.window_days)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
