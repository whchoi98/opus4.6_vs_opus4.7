"""Aggregation of CallResult lists into per-case statistics."""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from clients.base import CallResult


@dataclass(frozen=True)
class CaseAggregate:
    test_id: str
    backend: str
    auth_method: str
    model_id: str
    effort: str | None
    prompt_label: str
    n_runs: int
    n_success: int
    input_tokens_mean: float
    input_tokens_std: float
    output_tokens_mean: float
    output_tokens_std: float
    latency_mean: float
    latency_std: float
    thinking_chars_mean: float
    tool_calls_mean: float
    total_cost_usd: float


def _key(r: CallResult) -> tuple:
    return (r.test_id, r.backend, r.auth_method, r.model_id, r.effort, r.prompt_label)


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = statistics.fmean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return m, s


def aggregate_results(results: Iterable[CallResult]) -> dict[tuple, CaseAggregate]:
    groups: dict[tuple, list[CallResult]] = defaultdict(list)
    for r in results:
        groups[_key(r)].append(r)

    out: dict[tuple, CaseAggregate] = {}
    for key, runs in groups.items():
        successes = [r for r in runs if r.error is None]
        in_tok_m, in_tok_s = _mean_std([r.input_tokens for r in successes])
        out_tok_m, out_tok_s = _mean_std([r.output_tokens for r in successes])
        lat_m, lat_s = _mean_std([r.latency_s for r in successes])
        think_m, _ = _mean_std([r.thinking_chars for r in successes])
        tools_m, _ = _mean_std([r.tool_calls_count for r in successes])
        total_cost = sum(r.cost_usd for r in successes)
        test_id, backend, auth, model, effort, prompt = key
        out[key] = CaseAggregate(
            test_id=test_id, backend=backend, auth_method=auth,
            model_id=model, effort=effort, prompt_label=prompt,
            n_runs=len(runs), n_success=len(successes),
            input_tokens_mean=in_tok_m, input_tokens_std=in_tok_s,
            output_tokens_mean=out_tok_m, output_tokens_std=out_tok_s,
            latency_mean=lat_m, latency_std=lat_s,
            thinking_chars_mean=think_m, tool_calls_mean=tools_m,
            total_cost_usd=total_cost,
        )
    return out
