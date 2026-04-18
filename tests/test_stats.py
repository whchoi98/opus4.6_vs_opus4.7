from clients.base import CallResult
from stats import aggregate_results, CaseAggregate


def _make_result(run_index, input_tokens=37, output_tokens=100, latency=1.0, error=None):
    return CallResult(
        input_tokens=input_tokens, output_tokens=output_tokens,
        latency_s=latency, thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="low", prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.001,
        run_index=run_index, test_id="test_1", error=error,
    )


def test_aggregate_single_case_5_runs():
    results = [_make_result(i, latency=i + 1.0) for i in range(5)]
    agg = aggregate_results(results)
    assert len(agg) == 1
    key = ("test_1", "bedrock_runtime", "iam_role", "global.anthropic.claude-opus-4-7", "low", "proof")
    ca: CaseAggregate = agg[key]
    assert ca.n_runs == 5
    assert ca.n_success == 5
    assert ca.input_tokens_mean == 37.0
    assert ca.input_tokens_std == 0.0
    assert abs(ca.latency_mean - 3.0) < 1e-9
    assert ca.latency_std > 0


def test_aggregate_excludes_errors_from_stats():
    results = [_make_result(0, latency=1.0), _make_result(1, latency=2.0),
               _make_result(2, latency=999.0, error="ratelimit")]
    agg = aggregate_results(results)
    key = next(iter(agg))
    ca = agg[key]
    assert ca.n_runs == 3
    assert ca.n_success == 2
    assert abs(ca.latency_mean - 1.5) < 1e-9


def test_aggregate_groups_by_effort_and_prompt():
    r1 = _make_result(0)
    r2 = CallResult(
        input_tokens=37, output_tokens=100, latency_s=1.0,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="max", prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.01,
        run_index=0, test_id="test_1",
    )
    agg = aggregate_results([r1, r2])
    assert len(agg) == 2
