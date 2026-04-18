from unittest.mock import MagicMock

from clients.base import CallResult
from runner.execute import execute_case_with_retry, select_client


def test_select_client_bedrock_runtime():
    from clients.bedrock_runtime import BedrockRuntimeClient
    c = select_client("bedrock_runtime", "iam_role")
    assert isinstance(c, BedrockRuntimeClient)


def test_select_client_bedrock_mantle():
    from clients.bedrock_mantle import BedrockMantleClient
    c = select_client("bedrock_mantle", "iam_role")
    assert isinstance(c, BedrockMantleClient)


def _fake_result(run_index=0, error=None):
    return CallResult(
        input_tokens=10, output_tokens=10, latency_s=0.1,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="test",
        stop_reason="end_turn", cost_usd=0.0,
        run_index=run_index, test_id="test_x", error=error,
    )


def test_execute_case_with_retry_success_first_try():
    client = MagicMock()
    client.invoke.return_value = _fake_result()
    from cases.base import TestCase
    case = TestCase(name="n", test_id="t", backend="bedrock_runtime",
                    model_id="global.anthropic.claude-opus-4-7",
                    prompt="hi", prompt_label="p")
    r = execute_case_with_retry(client, case, run_index=0, max_attempts=3)
    assert r.error is None
    assert client.invoke.call_count == 1


def test_execute_case_with_retry_retries_on_5xx(monkeypatch):
    import anthropic
    client = MagicMock()
    client.invoke.side_effect = [
        anthropic.APIStatusError("server error", response=MagicMock(status_code=503), body=None),
        _fake_result(),
    ]
    from cases.base import TestCase
    case = TestCase(name="n", test_id="t", backend="bedrock_runtime",
                    model_id="global.anthropic.claude-opus-4-7",
                    prompt="hi", prompt_label="p")
    monkeypatch.setattr("runner.execute._backoff_seconds", lambda attempt: 0.01)
    r = execute_case_with_retry(client, case, run_index=0, max_attempts=3)
    assert r.error is None
    assert client.invoke.call_count == 2
