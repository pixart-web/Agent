import json

from app.evaluations.policy_suite import evaluate_policy_suite


def main() -> None:
    report = evaluate_policy_suite()
    print(json.dumps(report, indent=2))
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
