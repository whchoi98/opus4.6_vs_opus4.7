from runner.dispatch import collect_cases
from runner.preflight import check_auth_env


def test_collect_cases_all():
    cs = collect_cases(selected=["1", "2", "3", "4"])
    assert len(cs) == 21  # 5 + 4 + 2 + 10


def test_collect_cases_subset():
    cs = collect_cases(selected=["1", "3"])
    assert len(cs) == 7  # 5 + 2


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
