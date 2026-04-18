"""Shared types and helpers for client wrappers."""
from dataclasses import dataclass
from typing import Any, Optional

import config


@dataclass(frozen=True)
class CallResult:
    # Measurements
    input_tokens: int
    output_tokens: int
    latency_s: float
    thinking_chars: int
    tool_calls_count: int

    # Context for grouping
    backend: str
    auth_method: str
    model_id: str
    effort: Optional[str]
    prompt_label: str

    # Debugging / auditing
    stop_reason: str
    cost_usd: float
    run_index: int
    test_id: str

    # Cache telemetry (default 0 — non-caching calls leave these unset)
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    error: Optional[str] = None


def compute_cost_usd(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Compute USD cost for one call using PRICING from config.

    Cache writes are charged at 1.25x input rate; cache reads at 0.1x input rate.
    """
    key = config.model_key_from_id(model_id)
    p = config.PRICING[key]
    return (
        input_tokens / 1_000_000 * p["input"]
        + output_tokens / 1_000_000 * p["output"]
        + cache_creation_tokens / 1_000_000 * p["input"] * 1.25
        + cache_read_tokens / 1_000_000 * p["input"] * 0.10
    )


def parse_bedrock_response(
    resp: dict,
    *,
    latency_s: float,
    backend: str,
    auth_method: str,
    model_id: str,
    effort: Optional[str],
    prompt_label: str,
    run_index: int,
    test_id: str,
) -> CallResult:
    """Parse a Bedrock (or 1P — same shape) response JSON into a CallResult."""
    usage = resp.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0

    thinking_chars = 0
    tool_calls_count = 0
    for block in resp.get("content", []):
        btype = block.get("type")
        if btype == "thinking":
            thinking_chars += len(block.get("thinking", ""))
        elif btype == "tool_use":
            tool_calls_count += 1

    return CallResult(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_s=latency_s,
        thinking_chars=thinking_chars,
        tool_calls_count=tool_calls_count,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        backend=backend,
        auth_method=auth_method,
        model_id=model_id,
        effort=effort,
        prompt_label=prompt_label,
        stop_reason=resp.get("stop_reason", "unknown"),
        cost_usd=compute_cost_usd(
            model_id, input_tokens, output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        ),
        run_index=run_index,
        test_id=test_id,
    )
