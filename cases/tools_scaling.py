"""Test 8: Tool schema scaling — input token cost vs tool count.

Uses the same prompt ("Look up pricing for Bedrock in us-east-1 and eu-west-1")
with varying numbers of tool schemas attached (1, 5, 20). Measures how much
input tokens inflate as the toolset grows.

Each tool schema is kept similar in shape to avoid schema-size noise — only
the count varies.
"""
from cases.base import TestCase
import config


def _synth_tool(i: int) -> dict:
    """Synthesize a tool schema similar in size to our baseline Bedrock tools."""
    return {
        "name": f"query_service_{i:02d}",
        "description": (
            f"Query AWS service {i:02d} metadata including pricing, quotas, "
            f"and availability in a given region. Returns a structured JSON "
            f"response with service-specific details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {
                    "type": "string",
                    "description": f"The unique identifier for service {i:02d} resource.",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region code, e.g. 'us-east-1'.",
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["summary", "detailed", "full"],
                    "description": "Level of detail to include in the response.",
                },
            },
            "required": ["resource_id", "region"],
        },
    }


def _tools(n: int) -> list[dict]:
    return [_synth_tool(i) for i in range(n)]


_PROMPT = "Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for n in (1, 5, 20):
        for model, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
            out.append(TestCase(
                name=f"{model}-tools-{n:02d}",
                test_id="test_8",
                backend="bedrock_runtime",
                model_id=model_id,
                prompt=_PROMPT,
                prompt_label=f"tools-{n:02d}",
                max_tokens=400,
                tools=_tools(n),
            ))
    return out
