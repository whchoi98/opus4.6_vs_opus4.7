"""Execute a single TestCase, with retry handling and client dispatch."""
from __future__ import annotations

import time
from typing import Protocol

import anthropic
import requests

import config
from cases.base import TestCase
from clients.anthropic_1p import AnthropicOnePClient
from clients.base import CallResult
from clients.bedrock_mantle import BedrockMantleClient
from clients.bedrock_runtime import BedrockRuntimeClient


class _Client(Protocol):
    def invoke(self, *, model_id: str, prompt: str, prompt_label: str,
               max_tokens: int, effort: str | None = None,
               tools: list[dict] | None = None,
               run_index: int = 0, test_id: str = "") -> CallResult: ...


_CLIENT_CACHE: dict[tuple[str, str], _Client] = {}


def select_client(backend: str, auth_method: str) -> _Client:
    key = (backend, auth_method)
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]

    if backend == "bedrock_runtime":
        client = BedrockRuntimeClient(auth_method=auth_method)
    elif backend == "bedrock_mantle":
        client = BedrockMantleClient(auth_method=auth_method)
    elif backend == "1p":
        client = AnthropicOnePClient(auth_method=auth_method)
    else:
        raise ValueError(f"Unknown backend: {backend}")

    _CLIENT_CACHE[key] = client
    return client


def _backoff_seconds(attempt: int) -> float:
    return config.RETRY_BACKOFF_BASE_S * (2 ** attempt)


def execute_case_with_retry(
    client: _Client,
    case: TestCase,
    *,
    run_index: int,
    max_attempts: int = config.RETRY_MAX_ATTEMPTS,
) -> CallResult:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return client.invoke(
                model_id=case.model_id,
                prompt=case.prompt,
                prompt_label=case.prompt_label,
                max_tokens=case.max_tokens,
                effort=case.effort,
                tools=case.tools,
                run_index=run_index,
                test_id=case.test_id,
            )
        except anthropic.RateLimitError as e:
            last_exc = e
        except anthropic.APIStatusError as e:
            last_exc = e
            status = getattr(e, "status_code", None) or getattr(
                getattr(e, "response", None), "status_code", 0
            )
            if status and status < 500:
                break
        except requests.HTTPError as e:
            last_exc = e
            if e.response is not None and e.response.status_code < 500:
                break
        except Exception as e:
            last_exc = e
            break

        if attempt + 1 < max_attempts:
            time.sleep(_backoff_seconds(attempt))

    return CallResult(
        input_tokens=0, output_tokens=0, latency_s=0.0,
        thinking_chars=0, tool_calls_count=0,
        backend=case.backend, auth_method=case.auth_method,
        model_id=case.model_id, effort=case.effort,
        prompt_label=case.prompt_label,
        stop_reason="error", cost_usd=0.0,
        run_index=run_index, test_id=case.test_id,
        error=f"{type(last_exc).__name__}: {str(last_exc)[:200]}",
    )
