"""Test 3: parallel tool use."""
from cases.base import TestCase
from cases.prompts import TOOL_USE_PROMPT, TOOLS_SCHEMA
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(name="opus-4.7-tools", test_id="test_3",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=TOOL_USE_PROMPT, prompt_label="tools",
                 max_tokens=400, tools=TOOLS_SCHEMA),
        TestCase(name="opus-4.6-tools", test_id="test_3",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=TOOL_USE_PROMPT, prompt_label="tools",
                 max_tokens=400, tools=TOOLS_SCHEMA),
    ]
