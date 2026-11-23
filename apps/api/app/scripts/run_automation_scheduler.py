"""Continuously runs scheduled automations when they fall due, and fails AI runs that a dead
worker abandoned (`app.services.run_maintenance`).

Each iteration calls `AutomationService.run_due_schedules`, which advances the next due time
under the automation lock and deduplicates runs, so several schedulers (or a manual
`run_due_automations`) can never create the same command twice.
"""

import logging

from app.automations.service import AutomationService
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.scripts._loop import StopFlag, run_forever
from app.services.run_maintenance import fail_abandoned_runs

logger = logging.getLogger(__name__)


def run_once(service: AutomationService) -> int:
    runs = service.run_due_schedules()
    if runs:
        logger.info(
            "automation_schedules_processed",
            extra={
                "processed": len(runs),
                "completed": sum(item.status == "completed" for item in runs),
                "skipped": sum(item.status == "skipped" for item in runs),
            },
        )
    return len(runs)


def maintain() -> dict[str, int]:
    with SessionLocal() as session:
        return fail_abandoned_runs(session)


def run_pass(service: AutomationService) -> None:
    run_once(service)
    maintain()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    stop = StopFlag().install()
    service = AutomationService()
    run_forever(
        lambda: run_pass(service),
        name="automation_scheduler",
        interval_seconds=settings.automation_scheduler_interval_seconds,
        should_stop=lambda: stop.stopping,
    )


if __name__ == "__main__":
    main()
