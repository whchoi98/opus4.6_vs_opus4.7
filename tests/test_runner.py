from runner.dispatch import collect_cases
from runner.preflight import check_auth_env


def test_collect_cases_all():
    cs = collect_cases(selected=["1", "2", "3", "4", "5", "6", "7", "8", "9"])
    assert len(cs) == 49  # 5 + 4 + 2 + 10 + 2 + 8 + 4 + 6 + 8


def test_collect_cases_subset():
    cs = collect_cases(selected=["1", "3"])
    assert len(cs) == 7  # 5 + 2


def test_resolve_tests_all_excludes_deferred():
    """Test 5 (prompt caching) is deferred and must not be in the default 'all' run."""
    from run import resolve_tests
    ids = resolve_tests("all")
    assert "5" not in ids
    assert set(ids) == {"1", "2", "3", "4", "6", "7", "8", "9"}


def test_resolve_tests_explicit_5_still_allowed():
    """Deferred tests are still runnable when explicitly selected."""
    from run import resolve_tests
    ids = resolve_tests("5")
    assert ids == ["5"]


def test_check_auth_env_bedrock_with_key(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "x")
    ok, msg = check_auth_env(backends={"bedrock"})
    assert ok, msg


def test_check_auth_env_bedrock_missing(monkeypatch):
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    result = check_auth_env(backends={"bedrock"})
    assert isinstance(result, tuple) and len(result) == 2


def test_check_auth_env_1p_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ok, msg = check_auth_env(backends={"1p"})
    assert not ok
    assert "ANTHROPIC_API_KEY" in msg
