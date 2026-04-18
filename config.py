"""Central configuration — model IDs, endpoints, pricing, run parameters."""

MODELS_1P = {
    "opus-4.7": "claude-opus-4-7",
    "opus-4.6": "claude-opus-4-6",
}

MODELS_3P = {
    "opus-4.7": "global.anthropic.claude-opus-4-7",
    "opus-4.6": "global.anthropic.claude-opus-4-6-v1",
}

# USD per MTok — Bedrock Global inference profile pricing as of 2026-04.
# Regional profiles (us./eu./jp.) cost +$0.50/in, +$2.50/out and can be added if needed.
PRICING = {
    "opus-4.7": {"input": 5.00, "output": 25.00},
    "opus-4.6": {"input": 5.00, "output": 25.00},
}

BEDROCK_REGION = "us-east-1"
MANTLE_URL = f"https://bedrock-mantle.{BEDROCK_REGION}.api.aws/anthropic/v1/messages"

DEFAULT_RUNS = 5
DEFAULT_MAX_TOKENS = 1000
INTER_CALL_DELAY_S = 0.2
BACKEND_SWITCH_DELAY_S = 0.5
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_S = 2.0


def model_key_from_id(model_id: str) -> str:
    """Map a backend model ID to our 'opus-4.7' / 'opus-4.6' key for pricing."""
    if "opus-4-7" in model_id:
        return "opus-4.7"
    if "opus-4-6" in model_id:
        return "opus-4.6"
    raise ValueError(f"Unknown model id: {model_id}")
