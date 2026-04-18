"""Test 1: effort level vs token consumption."""
from cases.base import TestCase
from cases.prompts import PROOF_PROMPT
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for effort in ("low", "medium", "high", "max"):
        out.append(TestCase(
            name=f"opus-4.7-effort-{effort}",
            test_id="test_1",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=PROOF_PROMPT,
            prompt_label="proof",
            max_tokens=1000,
            effort=effort,
        ))
    out.append(TestCase(
        name="opus-4.6-native-adaptive",
        test_id="test_1",
        backend="bedrock_runtime",
        model_id=m46,
        prompt=PROOF_PROMPT,
        prompt_label="proof",
        max_tokens=1000,
    ))
    return out
