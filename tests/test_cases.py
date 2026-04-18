from cases.effort import cases as effort_cases
from cases.length import cases as length_cases
from cases.tools import cases as tool_cases


def test_effort_cases_count_and_ids():
    cs = effort_cases()
    assert len(cs) == 5  # 4.7 × 4 effort + 4.6 × 1
    assert {c.test_id for c in cs} == {"test_1"}
    efforts = {c.effort for c in cs if "opus-4-7" in c.model_id}
    assert efforts == {"low", "medium", "high", "max"}


def test_length_cases_count_and_prompts():
    cs = length_cases()
    assert len(cs) == 4
    assert {c.test_id for c in cs} == {"test_2"}
    labels = {c.prompt_label for c in cs}
    assert labels == {"short", "long"}


def test_tools_cases_count_and_tools():
    cs = tool_cases()
    assert len(cs) == 2
    assert {c.test_id for c in cs} == {"test_3"}
    for c in cs:
        assert c.tools is not None
        assert len(c.tools) == 2
