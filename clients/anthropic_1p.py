"""Wrapper around anthropic.Anthropic for the 1P (Anthropic direct) API."""
from __future__ import annotations

import time
from typing import Optional

import anthropic

from clients.base import CallResult, parse_bedrock_response


def build_kwargs_1p(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    effort: Optional[str],
    tools: Optional[list[dict]],
) -> dict:
    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        kwargs["tools"] = tools
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    return kwargs


class AnthropicOnePClient:
    def __init__(self, auth_method: str = "api_key"):
        self._client = anthropic.Anthropic()
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
    ) -> CallResult:
        kwargs = build_kwargs_1p(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools,
        )
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = time.perf_counter() - t0
        resp_dict = {
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
            "content": [_block_to_dict(b) for b in resp.content],
            "stop_reason": resp.stop_reason,
        }
        return parse_bedrock_response(
            resp_dict, latency_s=latency, backend="1p",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )


def _block_to_dict(block) -> dict:
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
