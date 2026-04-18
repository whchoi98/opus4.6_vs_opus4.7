from clients.base import CallResult, compute_cost_usd, parse_bedrock_response


def test_callresult_is_frozen():
    r = CallResult(
        input_tokens=10, output_tokens=20, latency_s=1.5,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="short",
        stop_reason="end_turn", cost_usd=0.0005,
        run_index=0, test_id="test_1",
    )
    try:
        r.input_tokens = 99
        assert False, "should be frozen"
    except Exception:
        pass


def test_compute_cost_opus_47():
    cost = compute_cost_usd("global.anthropic.claude-opus-4-7", input_tokens=1000, output_tokens=500)
    assert abs(cost - (1000 / 1_000_000 * 5.0 + 500 / 1_000_000 * 25.0)) < 1e-9


def test_compute_cost_opus_46():
    cost = compute_cost_usd("global.anthropic.claude-opus-4-6-v1", input_tokens=2000, output_tokens=0)
    assert abs(cost - (2000 / 1_000_000 * 5.0)) < 1e-9


def test_parse_bedrock_response_basic():
    resp = {
        "usage": {"input_tokens": 37, "output_tokens": 926},
        "content": [{"type": "text", "text": "hello"}],
        "stop_reason": "end_turn",
    }
    result = parse_bedrock_response(
        resp, latency_s=8.24, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="low", prompt_label="proof", run_index=0, test_id="test_1",
    )
    assert result.input_tokens == 37
    assert result.output_tokens == 926
    assert result.thinking_chars == 0
    assert result.tool_calls_count == 0


def test_parse_bedrock_response_with_thinking():
    resp = {
        "usage": {"input_tokens": 23, "output_tokens": 958},
        "content": [
            {"type": "thinking", "thinking": "x" * 856},
            {"type": "text", "text": "hello"},
        ],
        "stop_reason": "end_turn",
    }
    r = parse_bedrock_response(
        resp, latency_s=15.1, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-6-v1",
        effort=None, prompt_label="proof", run_index=0, test_id="test_1",
    )
    assert r.thinking_chars == 856


def test_parse_bedrock_response_counts_tool_uses():
    resp = {
        "usage": {"input_tokens": 888, "output_tokens": 270},
        "content": [
            {"type": "tool_use", "id": "a", "name": "x", "input": {}},
            {"type": "tool_use", "id": "b", "name": "y", "input": {}},
            {"type": "tool_use", "id": "c", "name": "z", "input": {}},
            {"type": "tool_use", "id": "d", "name": "w", "input": {}},
        ],
        "stop_reason": "tool_use",
    }
    r = parse_bedrock_response(
        resp, latency_s=2.13, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="tools", run_index=0, test_id="test_3",
    )
    assert r.tool_calls_count == 4
    assert r.stop_reason == "tool_use"
