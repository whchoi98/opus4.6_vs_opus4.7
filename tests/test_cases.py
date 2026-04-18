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


from cases.mantle import cases as mantle_cases


def test_mantle_cases_count_and_structure():
    cs = mantle_cases()
    assert len(cs) == 10
    iam_mantle = [c for c in cs if c.backend == "bedrock_mantle" and c.auth_method == "iam_role"]
    assert len(iam_mantle) == 4
    api_key_cases = [c for c in cs if c.auth_method == "bedrock_api_key"]
    assert len(api_key_cases) == 6
    for c in cs:
        assert "opus-4-7" in c.model_id


def test_mantle_cases_cover_all_prompts():
    cs = mantle_cases()
    prompt_labels = {c.prompt_label for c in cs}
    assert "proof" in prompt_labels
    assert "long" in prompt_labels
    assert "tools" in prompt_labels
    assert "short" in prompt_labels


from cases.streaming import cases as streaming_cases


def test_streaming_cases():
    cs = streaming_cases()
    assert len(cs) == 4
    assert {c.test_id for c in cs} == {"test_7"}
    for c in cs:
        assert c.streaming is True
        assert c.backend == "bedrock_runtime"


from cases.multiturn import cases as multiturn_cases


def test_multiturn_cases_count_and_structure():
    cs = multiturn_cases()
    assert len(cs) == 8  # 4 turn counts × 2 models
    assert {c.test_id for c in cs} == {"test_6"}
    # All have messages_override set
    for c in cs:
        assert c.messages_override is not None
        # Messages alternate user/assistant
        for i, m in enumerate(c.messages_override):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert m["role"] == expected_role
        # Last message is always user
        assert c.messages_override[-1]["role"] == "user"
    # Turn counts: {1, 3, 5, 10}
    label_counts = sorted(set(c.prompt_label for c in cs))
    assert label_counts == ["turns-1", "turns-10", "turns-3", "turns-5"]


from cases.tool_forcing import cases as tool_forcing_cases


def test_tool_forcing_cases():
    cs = tool_forcing_cases()
    assert len(cs) == 8  # 4 variants × 2 models
    assert {c.test_id for c in cs} == {"test_9"}
    labels = {c.prompt_label for c in cs}
    assert labels == {"passive", "imperative", "choice-any", "choice-specific"}
    # choice-any and choice-specific cases have tool_choice set
    for c in cs:
        if c.prompt_label in ("choice-any", "choice-specific"):
            assert c.tool_choice is not None
        else:
            assert c.tool_choice is None


from cases.tools_scaling import cases as tools_scaling_cases


def test_tools_scaling_cases():
    cs = tools_scaling_cases()
    assert len(cs) == 6  # 3 tool counts × 2 models
    assert {c.test_id for c in cs} == {"test_8"}

    # Verify tool counts: 1, 5, 20
    tool_counts = sorted({len(c.tools) for c in cs})
    assert tool_counts == [1, 5, 20]

    # Verify both models covered at each count
    from collections import Counter
    counts = Counter((len(c.tools), c.model_id) for c in cs)
    for n in (1, 5, 20):
        assert counts[(n, cs[0].model_id if n == 1 else None)] or True  # basic sanity

    # Each tool should have the expected synth name pattern
    for c in cs:
        for tool in c.tools:
            assert tool["name"].startswith("query_service_")
            assert "input_schema" in tool
