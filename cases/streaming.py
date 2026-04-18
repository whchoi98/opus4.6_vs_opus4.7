"""Test 7: Streaming TTFT — time to first token.

Measures latency from request send to first content event. Chatbot UX and
voice agents care about TTFT more than total response time.
"""
from cases.base import TestCase
from cases.prompts import SHORT_PROMPT, LONG_PROMPT
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(
            name="opus-4.7-stream-short",
            test_id="test_7",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=SHORT_PROMPT,
            prompt_label="stream-short",
            max_tokens=300,
            streaming=True,
        ),
        TestCase(
            name="opus-4.7-stream-long",
            test_id="test_7",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=LONG_PROMPT,
            prompt_label="stream-long",
            max_tokens=300,
            streaming=True,
        ),
        TestCase(
            name="opus-4.6-stream-short",
            test_id="test_7",
            backend="bedrock_runtime",
            model_id=m46,
            prompt=SHORT_PROMPT,
            prompt_label="stream-short",
            max_tokens=300,
            streaming=True,
        ),
        TestCase(
            name="opus-4.6-stream-long",
            test_id="test_7",
            backend="bedrock_runtime",
            model_id=m46,
            prompt=LONG_PROMPT,
            prompt_label="stream-long",
            max_tokens=300,
            streaming=True,
        ),
    ]
