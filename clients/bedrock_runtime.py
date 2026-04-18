"""Wrapper around anthropic.AnthropicBedrock for the bedrock-runtime endpoint.

Supports two auth paths, selected via auth_method:

- "iam_role": explicitly passes frozen IAM credentials (access_key, secret_key,
  session_token) to AnthropicBedrock, obtained from the boto3 credential chain
  with AWS_BEARER_TOKEN_BEDROCK temporarily hidden. Prevents the SDK's internal
  boto3 session from silently resolving to the bearer token when both are set.

- "bedrock_api_key": verifies AWS_BEARER_TOKEN_BEDROCK is present, then lets
  AnthropicBedrock use the default credential chain — which will pick up the
  bearer token and sign requests with Authorization: Bearer <token>.

Without this separation Test 4 cases 5/7/9 (auth comparison) would silently
use the same auth as the iam_role baseline, producing misleading benchmarks.

Credential caching note: for "iam_role", the frozen credentials snapshot does
not auto-refresh. Benchmarks >1 hour on temporary IAM credentials (STS/IMDS)
may see 403 errors. For long-running use, instantiate a fresh client.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import anthropic
from botocore.session import Session

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
    tool_choice: Optional[dict] = None,
    system_prompt: Optional[str] = None,
    system_cached: bool = False,
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
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if system_prompt is not None:
        if system_cached:
            kwargs["system"] = [{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }]
        else:
            kwargs["system"] = system_prompt
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    return kwargs


def _build_runtime_sdk_client(region: str, auth_method: str):
    """Construct an AnthropicBedrock SDK client pinned to the specified auth method.

    The SDK detects AWS_BEARER_TOKEN_BEDROCK at construction time and refuses
    to accept explicit aws_* credentials alongside it. So for iam_role we must
    hide the bearer token env var across the ENTIRE AnthropicBedrock() call,
    not just during credential resolution.
    """
    if auth_method == "iam_role":
        saved = os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
        try:
            creds = Session().get_credentials()
            if creds is None:
                raise RuntimeError(
                    "auth_method='iam_role' requires IAM credentials "
                    "(AWS_PROFILE / AWS_ACCESS_KEY_ID / instance role) — none found."
                )
            frozen = creds.get_frozen_credentials()
            client = anthropic.AnthropicBedrock(
                aws_region=region,
                aws_access_key=frozen.access_key,
                aws_secret_key=frozen.secret_key,
                aws_session_token=frozen.token,
            )
        finally:
            if saved is not None:
                os.environ["AWS_BEARER_TOKEN_BEDROCK"] = saved
        return client
    if auth_method == "bedrock_api_key":
        if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
            raise RuntimeError(
                "auth_method='bedrock_api_key' requires AWS_BEARER_TOKEN_BEDROCK "
                "to be set in the environment."
            )
        # Let the SDK's default credential chain pick up the bearer token.
        return anthropic.AnthropicBedrock(aws_region=region)
    raise ValueError(
        f"Runtime client auth_method must be 'iam_role' or 'bedrock_api_key'; "
        f"got {auth_method!r}"
    )


class BedrockRuntimeClient:
    def __init__(self, region: str = config.BEDROCK_REGION, auth_method: str = "iam_role"):
        self._region = region
        self._auth_method = auth_method
        self._client = _build_runtime_sdk_client(region, auth_method)

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
        tool_choice: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        system_cached: bool = False,
    ) -> CallResult:
        kwargs = build_kwargs(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools, use_cache=use_cache,
            messages_override=messages_override, tool_choice=tool_choice,
            system_prompt=system_prompt, system_cached=system_cached,
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


    def invoke_streaming(
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
        tool_choice: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        system_cached: bool = False,
    ) -> CallResult:
        """Invoke via streaming, measuring TTFT (time to first content event)."""
        kwargs = build_kwargs(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools, tool_choice=tool_choice,
            system_prompt=system_prompt, system_cached=system_cached,
        )

        t0 = time.perf_counter()
        ttft = None
        final_message = None

        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                if ttft is None and getattr(event, "type", None) == "content_block_delta":
                    ttft = time.perf_counter() - t0
            final_message = stream.get_final_message()

        latency = time.perf_counter() - t0

        resp_dict = {
            "usage": {
                "input_tokens": final_message.usage.input_tokens,
                "output_tokens": final_message.usage.output_tokens,
                "cache_creation_input_tokens": getattr(final_message.usage, "cache_creation_input_tokens", 0) or 0,
                "cache_read_input_tokens": getattr(final_message.usage, "cache_read_input_tokens", 0) or 0,
            },
            "content": [_block_to_dict(b) for b in final_message.content],
            "stop_reason": final_message.stop_reason,
        }
        return parse_bedrock_response(
            resp_dict, latency_s=latency, backend="bedrock_runtime",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
            ttft_s=ttft,
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
