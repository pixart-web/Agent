from sqlalchemy.exc import OperationalError

from app.scripts._loop import run_forever


def test_dispatcher_loop_survives_database_outage_and_backs_off() -> None:
    calls: list[str] = []
    sleeps: list[float] = []
    outcomes = iter(["down", "down", "ok", "ok"])

    def step() -> None:
        outcome = next(outcomes)
        calls.append(outcome)
        if outcome == "down":
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    run_forever(
        step,
        name="test",
        interval_seconds=2,
        should_stop=lambda: len(calls) >= 4,
        sleep=sleeps.append,
    )

    assert calls == ["down", "down", "ok", "ok"]
    assert sleeps == [4, 8, 2, 2]  # exponential backoff while down, normal interval after


def test_dispatcher_loop_backoff_is_capped_and_stops_on_flag() -> None:
    sleeps: list[float] = []
    count = {"n": 0}

    def failing() -> None:
        count["n"] += 1
        raise RuntimeError("still down")

    run_forever(
        failing,
        name="test",
        interval_seconds=2,
        should_stop=lambda: count["n"] >= 8,
        sleep=sleeps.append,
        max_backoff_seconds=30,
    )
    assert max(sleeps) == 30
    assert count["n"] == 8
