"""Collect test cases from case modules based on CLI selection."""
from cases import effort, length, tools, mantle, caching, multiturn, streaming
from cases.base import TestCase


TEST_MODULES = {
    "1": effort,
    "2": length,
    "3": tools,
    "4": mantle,
    "5": caching,
    "6": multiturn,
    "7": streaming,
}


def collect_cases(selected: list[str]) -> list[TestCase]:
    """selected is a list of test ids like ['1', '2', '3', '4'] or subset."""
    out: list[TestCase] = []
    for tid in selected:
        module = TEST_MODULES.get(tid)
        if module is None:
            raise ValueError(f"Unknown test id: {tid}")
        out.extend(module.cases())
    return out
