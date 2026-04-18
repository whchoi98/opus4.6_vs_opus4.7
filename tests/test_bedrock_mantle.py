from clients.bedrock_mantle import build_body


def test_build_body_basic():
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort=None, tools=None,
    )
    assert b["anthropic_version"] == "bedrock-2023-05-31"
    assert b["model"] == "global.anthropic.claude-opus-4-7"
    assert b["max_tokens"] == 100
    assert b["messages"] == [{"role": "user", "content": "hi"}]
    assert "thinking" not in b


def test_build_body_opus47_with_effort():
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort="max", tools=None,
    )
    assert b["thinking"] == {"type": "adaptive"}
    assert b["output_config"] == {"effort": "max"}


def test_build_body_with_tools():
    tools = [{"name": "x", "description": "d",
              "input_schema": {"type": "object", "properties": {}}}]
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort=None, tools=tools,
    )
    assert b["tools"] == tools
