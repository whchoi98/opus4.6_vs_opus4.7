"""Test 4: Mantle endpoint cross-check + IAM vs Bedrock-API-key auth comparison.

Cases 1-4 (mantle / iam_role): parity check — Mantle should produce identical
token counts to runtime; latency may differ slightly.

Cases 5-10 (bedrock_api_key on both endpoints): isolate the auth-method
latency effect by pairing each auth_key case with an iam_role baseline.
"""
from cases.base import TestCase
from cases.prompts import PROOF_PROMPT, SHORT_PROMPT, LONG_PROMPT, TOOL_USE_PROMPT, TOOLS_SCHEMA
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    out: list[TestCase] = []

    # 1-4: Mantle parity check with iam_role
    out.append(TestCase(name="mantle-iam-short", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400,
                       auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-long", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-proof-max", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-tools", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="iam_role"))

    # 5-10: bedrock_api_key auth on both endpoints
    out.append(TestCase(name="runtime-apikey-long", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-long", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="bedrock_api_key"))
    out.append(TestCase(name="runtime-apikey-proof-max", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-proof-max", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="bedrock_api_key"))
    out.append(TestCase(name="runtime-apikey-tools", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-tools", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="bedrock_api_key"))
    return out
