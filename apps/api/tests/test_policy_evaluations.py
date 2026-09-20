from app.evaluations.policy_suite import evaluate_policy_suite


def test_policy_quality_suite_passes_all_versioned_cases() -> None:
    report = evaluate_policy_suite()
    assert report["suite"] == "policy_quality_v1"
    assert report["total"] >= 6
    assert report["passed"] == report["total"]
    assert report["pass_rate"] == 1.0
