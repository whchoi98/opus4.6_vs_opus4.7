"""Test 9: Tool use forcing — does prompt/tool_choice rescue 4.7's tool refusal?

Test 8 found that 4.7 abandons tools as the menu grows (0 calls at 20 tools).
Test 9 tries four strategies on the same 20-tool environment:

- passive: the same prompt used in Test 8 (baseline)
- imperative: prompt explicitly requires tool use
- tool_choice_any: API-level forcing via tool_choice={"type": "any"}
- tool_choice_specific: forces a particular tool by name
"""
from cases.base import TestCase
from cases.tools_scaling import _synth_tool
import config


_TOOLS_20 = [_synth_tool(i) for i in range(20)]

_PASSIVE = "Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."

_IMPERATIVE = (
    "You must use the available tools to look up pricing and limits for "
    "Bedrock in us-east-1 and eu-west-1. Call the appropriate tools "
    "directly — do not answer from your own knowledge."
)


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for model_label, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
        out.append(TestCase(
            name=f"{model_label}-passive",
            test_id="test_9",
            backend="bedrock_runtime",
            model_id=model_id,
            prompt=_PASSIVE,
            prompt_label="passive",
            max_tokens=400,
            tools=_TOOLS_20,
        ))
        out.append(TestCase(
            name=f"{model_label}-imperative",
            test_id="test_9",
            backend="bedrock_runtime",
            model_id=model_id,
            prompt=_IMPERATIVE,
            prompt_label="imperative",
            max_tokens=400,
            tools=_TOOLS_20,
        ))
        out.append(TestCase(
            name=f"{model_label}-choice-any",
            test_id="test_9",
            backend="bedrock_runtime",
            model_id=model_id,
            prompt=_PASSIVE,
            prompt_label="choice-any",
            max_tokens=400,
            tools=_TOOLS_20,
            tool_choice={"type": "any"},
        ))
        out.append(TestCase(
            name=f"{model_label}-choice-specific",
            test_id="test_9",
            backend="bedrock_runtime",
            model_id=model_id,
            prompt=_PASSIVE,
            prompt_label="choice-specific",
            max_tokens=400,
            tools=_TOOLS_20,
            tool_choice={"type": "tool", "name": "query_service_00"},
        ))
    return out
