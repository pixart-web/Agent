from app.operations.load_probe import is_loopback_url, percentile


def test_load_probe_defaults_are_local_only() -> None:
    assert is_loopback_url("http://127.0.0.1:8000")
    assert is_loopback_url("http://localhost:8000")
    assert is_loopback_url("http://[::1]:8000")
    assert not is_loopback_url("https://api.example.org")
    assert not is_loopback_url("not-a-url")


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([], 0.95) is None
    assert percentile(list(range(1, 101)), 0.95) == 95
