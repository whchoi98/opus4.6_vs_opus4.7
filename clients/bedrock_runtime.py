"""Wrapper around anthropic.AnthropicBedrock for the bedrock-runtime endpoint."""
from __future__ import annotations

import time
from typing import Optional

import anthropic

import config
from clients.base import CallResult, parse_bedrock_response


def build_kwargs(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    effort: Optional[str],
    tools: Optional[list[dict]],
    use_cache: bool = False,
    messages_override: Optional[list[dict]] = None,
) -> dict:
    """Build the kwargs dict for anthropic.AnthropicBedrock.messages.create.

    Handles the API shape divergence between Opus 4.7 (thinking.adaptive +
    output_config.effort) and Opus 4.6 (no thinking kwarg by default).
    When use_cache=True, wraps the user message content in a list with
    cache_control={"type": "ephemeral"} to enable prompt caching.
    When messages_override is provided, it is used verbatim as the messages
    list (e.g. for multi-turn conversation benchmarks).
    """
    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
    }
    if messages_override is not None:
        kwargs["messages"] = messages_override
    elif use_cache:
        kwargs["messages"] = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}],
        }]
    else:
        kwargs["messages"] = [{"role": "user", "content": prompt}]
    if tools:
        kwargs["tools"] = tools
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    return kwargs


class BedrockRuntimeClient:
    def __init__(self, region: str = config.BEDROCK_REGION, auth_method: str = "iam_role"):
        self._client = anthropic.AnthropicBedrock(aws_region=region)
        self._region = region
        self._auth_method = auth_method

    def invoke(
        self,
        *,
        model_id: str,
        prompt: str,
        prompt_label: str,
        max_tokens: int,
        effort: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        run_index: int = 0,
        test_id: str = "",
        use_cache: bool = False,
        messages_override: Optional[list[dict]] = None,
    ) -> CallResult:
        kwargs = build_kwargs(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools, use_cache=use_cache,
            messages_override=messages_override,
        )
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = time.perf_counter() - t0
        resp_dict = {
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
                "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
            },
            "content": [_block_to_dict(b) for b in resp.content],
            "stop_reason": resp.stop_reason,
        }
        return parse_bedrock_response(
            resp_dict, latency_s=latency, backend="bedrock_runtime",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )


def _block_to_dict(block) -> dict:
    """Convert an anthropic content block to the dict shape parse_bedrock_response expects."""
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if btype == "thinking":
        return {"type": "thinking", "thinking": getattr(block, "thinking", "")}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }
    return {"type": btype or "unknown"}
