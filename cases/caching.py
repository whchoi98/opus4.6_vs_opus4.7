"""Test 5: Prompt caching — measure cache hit rate and cost savings.

Each case runs N times. Run 0 writes to cache (cache_creation_tokens > 0).
Runs 1..N-1 read from cache (cache_read_tokens > 0, provided they occur
within the 5-minute cache TTL).
"""
from cases.base import TestCase
from cases.prompts import LONG_PROMPT
import config


# Pad the long prompt to ensure we clear the 1024-token cache minimum.
# The Korean code-review prompt is ~1700 chars ~= 700-900 tokens; we repeat it
# to guarantee we're over the threshold for both 4.7 and 4.6 tokenizers.
_LONG_CACHEABLE_PROMPT = LONG_PROMPT + "\n\n---\n\n" + LONG_PROMPT


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(
            name="opus-4.7-cache",
            test_id="test_5",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=_LONG_CACHEABLE_PROMPT,
            prompt_label="cache-long",
            max_tokens=200,
            use_cache=True,
        ),
        TestCase(
            name="opus-4.6-cache",
            test_id="test_5",
            backend="bedrock_runtime",
            model_id=m46,
            prompt=_LONG_CACHEABLE_PROMPT,
            prompt_label="cache-long",
            max_tokens=200,
            use_cache=True,
        ),
    ]
