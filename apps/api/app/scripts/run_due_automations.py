import json

from app.automations.service import AutomationService


def main() -> None:
    runs = AutomationService().run_due_schedules()
    print(
        json.dumps(
            {
                "processed": len(runs),
                "completed": sum(item.status == "completed" for item in runs),
                "skipped": sum(item.status == "skipped" for item in runs),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
