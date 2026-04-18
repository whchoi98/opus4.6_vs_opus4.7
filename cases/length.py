"""Test 2: prompt length scaling."""
from cases.base import TestCase
from cases.prompts import SHORT_PROMPT, LONG_PROMPT
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(name="opus-4.7-short", test_id="test_2",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400),
        TestCase(name="opus-4.7-long", test_id="test_2",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=LONG_PROMPT, prompt_label="long", max_tokens=400),
        TestCase(name="opus-4.6-short", test_id="test_2",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400),
        TestCase(name="opus-4.6-long", test_id="test_2",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=LONG_PROMPT, prompt_label="long", max_tokens=400),
    ]
