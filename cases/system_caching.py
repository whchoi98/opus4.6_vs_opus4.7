"""Test 12: System prompt caching — does Bedrock honor cache_control on system?

Test 5 found user-prompt caching returned zero cache tokens on Bedrock.
Test 12 checks whether the SYSTEM prompt path behaves differently —
system prompts are where caching would matter most in production agent
pipelines (long, stable instructions reused across thousands of calls).
"""
from cases.base import TestCase
from cases.prompts import SYSTEM_PROMPT_LONG
import config


# Short user message keeps the test focused on the system-prompt caching signal
_USER_MSG = "Review this architecture: a simple API Gateway + Lambda + DynamoDB backend for a 100K-user mobile app. Identify the top risk."


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(
            name="opus-4.7-system-cached",
            test_id="test_12",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=_USER_MSG,
            prompt_label="system-cached",
            max_tokens=400,
            system_prompt=SYSTEM_PROMPT_LONG,
            system_cached=True,
        ),
        TestCase(
            name="opus-4.6-system-cached",
            test_id="test_12",
            backend="bedrock_runtime",
            model_id=m46,
            prompt=_USER_MSG,
            prompt_label="system-cached",
            max_tokens=400,
            system_prompt=SYSTEM_PROMPT_LONG,
            system_cached=True,
        ),
    ]
