from clients.anthropic_1p import build_kwargs_1p


def test_build_kwargs_1p_opus_47_effort():
    k = build_kwargs_1p(
        model_id="claude-opus-4-7", prompt="hi", max_tokens=200,
        effort="medium", tools=None,
    )
    assert k["model"] == "claude-opus-4-7"
    assert k["max_tokens"] == 200
    assert k["thinking"] == {"type": "adaptive"}
    assert k["extra_body"] == {"output_config": {"effort": "medium"}}


def test_build_kwargs_1p_opus_46_default():
    k = build_kwargs_1p(
        model_id="claude-opus-4-6", prompt="hi", max_tokens=200,
        effort=None, tools=None,
    )
    assert "thinking" not in k
