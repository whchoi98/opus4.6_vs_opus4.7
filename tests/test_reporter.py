import json
from pathlib import Path

from clients.base import CallResult
from stats import aggregate_results
from reporter import write_raw_json, write_aggregated_json, write_markdown_report


def _make_result(run_index=0, test_id="test_1", effort="low"):
    return CallResult(
        input_tokens=37, output_tokens=100, latency_s=1.5,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=effort, prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.005,
        run_index=run_index, test_id=test_id,
    )


def test_write_raw_json(tmp_path: Path):
    results = [_make_result(i) for i in range(3)]
    meta = {"sdk_version": "0.96.0", "region": "us-east-1"}
    out = tmp_path / "raw.json"
    write_raw_json(results, meta, out)
    data = json.loads(out.read_text())
    assert data["meta"]["sdk_version"] == "0.96.0"
    assert len(data["results"]) == 3
    assert data["results"][0]["input_tokens"] == 37


def test_write_aggregated_json(tmp_path: Path):
    results = [_make_result(i) for i in range(5)]
    agg = aggregate_results(results)
    out = tmp_path / "aggregated.json"
    write_aggregated_json(agg, out)
    data = json.loads(out.read_text())
    assert len(data) == 1
    entry = data[0]
    assert entry["test_id"] == "test_1"
    assert entry["n_runs"] == 5
    assert entry["n_success"] == 5
    assert entry["input_tokens_mean"] == 37.0


def test_write_markdown_report(tmp_path: Path):
    results = [_make_result(i) for i in range(5)]
    agg = aggregate_results(results)
    out = tmp_path / "report.md"
    meta = {
        "sdk_version": "0.96.0", "region": "us-east-1",
        "backends": ["bedrock_runtime"],
        "total_calls": 5, "total_cost_usd": 0.025,
        "wall_time_s": 15.2, "start_ts": "2026-04-18T12:00:00",
    }
    write_markdown_report(results, agg, meta, out)
    text = out.read_text()
    assert "Opus 4.7 vs 4.6 Benchmark Report" in text
    assert "sdk_version" in text or "SDK" in text
    assert "Test 1" in text
    assert "37" in text
