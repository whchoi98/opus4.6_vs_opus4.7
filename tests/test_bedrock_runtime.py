from clients.bedrock_runtime import build_kwargs


def test_build_kwargs_opus_47_with_effort():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort="low", tools=None,
    )
    assert k["model"] == "global.anthropic.claude-opus-4-7"
    assert k["max_tokens"] == 100
    assert k["messages"] == [{"role": "user", "content": "hello"}]
    assert k["thinking"] == {"type": "adaptive"}
    assert k["extra_body"] == {"output_config": {"effort": "low"}}
    assert "tools" not in k


def test_build_kwargs_opus_47_no_effort():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort=None, tools=None,
    )
    assert "thinking" not in k
    assert "extra_body" not in k


def test_build_kwargs_opus_46_no_thinking():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-6-v1",
        prompt="hello", max_tokens=100, effort=None, tools=None,
    )
    assert "thinking" not in k


def test_build_kwargs_with_tools():
    tools = [{"name": "x", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort=None, tools=tools,
    )
    assert k["tools"] == tools
