"""Test 13: Multi-turn knee-point — fine-grained resolution between 10 and 20 turns.

Test 6 (up to 10 turns) and Test 10 (10/20/30/50/100 turns) showed 4.7 latency
jumps from ~3.95s at 10 turns to ~4.99s at 20 turns (+26%). This test fills in
the 11/13/15/17/19 range to locate the exact knee-point.
"""
from cases.base import TestCase
from cases.multiturn import _build_messages_extended
import config


_FINAL_USER_MSG = (
    "Given everything we've discussed across this entire conversation, "
    "please write me a concise single-day itinerary for Saturday with times."
)


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for n in (11, 13, 15, 17, 19):
        msgs = _build_messages_extended(n, _FINAL_USER_MSG)
        for model_label, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
            out.append(TestCase(
                name=f"{model_label}-knee-{n:02d}",
                test_id="test_13",
                backend="bedrock_runtime",
                model_id=model_id,
                prompt=_FINAL_USER_MSG,
                prompt_label=f"knee-{n:02d}",
                max_tokens=300,
                messages_override=msgs,
            ))
    return out
