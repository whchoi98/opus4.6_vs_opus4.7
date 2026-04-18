"""Test 11: Language/code decomposition — isolate what drives overhead reduction.

Test 2 found Korean+code had +13% overhead vs English short's +43%. This test
separates the two factors by running four prompt variants:

- english: ~350-word English prose
- korean: ~350-어절 Korean prose (same topic)
- code: ~350-LOC Python code (English identifiers)
- korean_code: Korean prose + embedded Python code (existing LONG_PROMPT)
"""
from cases.base import TestCase
from cases.prompts import (
    DECOMP_ENGLISH_PROMPT, DECOMP_KOREAN_PROMPT, DECOMP_CODE_PROMPT, LONG_PROMPT,
)
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    variants = [
        ("english", DECOMP_ENGLISH_PROMPT),
        ("korean", DECOMP_KOREAN_PROMPT),
        ("code", DECOMP_CODE_PROMPT),
        ("korean_code", LONG_PROMPT),
    ]
    out: list[TestCase] = []
    for label, prompt in variants:
        for model_label, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
            out.append(TestCase(
                name=f"{model_label}-{label}",
                test_id="test_11",
                backend="bedrock_runtime",
                model_id=model_id,
                prompt=prompt,
                prompt_label=label,
                max_tokens=400,
            ))
    return out
