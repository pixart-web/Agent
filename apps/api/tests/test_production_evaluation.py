from app.operations.evaluation import _evaluation, _p95, evaluate_production


def test_p95_and_rate_are_deterministic() -> None:
    assert _p95([]) is None
    assert _p95(list(range(1, 101))) == 95
    value = _evaluation(4, 3, [10, 20, 30, 40])
    assert value.success_rate == 0.75
    assert value.p95_latency_ms == 40


def test_empty_database_report_does_not_claim_readiness(db_session) -> None:
    report = evaluate_production(db_session, window_days=30)
    assert report.supervisor.total == 0
    assert report.supervisor.success_rate is None
    assert report.supervisor_cost_by_currency == {}
    assert report.sufficient_sample is False
