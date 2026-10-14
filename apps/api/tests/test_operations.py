def test_operations_overview_and_analytics_are_workspace_scoped(client, db_session) -> None:
    from tests.test_specialized_agents import ready_task

    headers, _command, _task = ready_task(
        client, db_session, "sales", email="operations@example.com"
    )
    overview = client.get("/api/v1/operations/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    data = overview.json()
    assert data["pending_tasks"] == 1
    assert data["active_commands"] == 1
    assert data["pending_approvals"] == 0
    assert data["recent_executions"] == []

    analytics = client.get("/api/v1/operations/analytics?days=30", headers=headers)
    assert analytics.status_code == 200, analytics.text
    report = analytics.json()
    assert report["period_days"] == 30
    assert report["totals"]["commands"] == 1
    assert report["totals"]["agent_runs"] == 0
    assert report["estimated_cost_minor"] is None
    assert report["cost_status"] == "unavailable"
    assert len(report["trends"]) == 30


def test_operations_require_authentication(client) -> None:
    response = client.get("/api/v1/operations/overview")
    assert response.status_code == 401
