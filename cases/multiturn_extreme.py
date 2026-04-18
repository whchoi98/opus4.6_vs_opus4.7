"""Test 10: Multi-turn extreme stress — does 4.7's latency plateau hold at 100 turns?

Test 6 showed 4.7 latency stays flat at ~4.05s from turn 3 to turn 10.
Test 10 extends to 10/20/30/50/100 turns to find the knee-point (if any).
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
    for n in (10, 20, 30, 50, 100):
        msgs = _build_messages_extended(n, _FINAL_USER_MSG)
        for model_label, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
            out.append(TestCase(
                name=f"{model_label}-xturns-{n:03d}",
                test_id="test_10",
                backend="bedrock_runtime",
                model_id=model_id,
                prompt=_FINAL_USER_MSG,
                prompt_label=f"xturns-{n:03d}",
                max_tokens=300,
                messages_override=msgs,
            ))
    return out
