import pytest

import config


def test_models_3p_has_both_models():
    assert config.MODELS_3P["opus-4.7"] == "global.anthropic.claude-opus-4-7"
    assert config.MODELS_3P["opus-4.6"] == "global.anthropic.claude-opus-4-6-v1"


def test_models_1p_has_both_models():
    assert config.MODELS_1P["opus-4.7"] == "claude-opus-4-7"
    assert config.MODELS_1P["opus-4.6"] == "claude-opus-4-6"


def test_pricing_matches_apr16_blog():
    for model in ("opus-4.7", "opus-4.6"):
        assert config.PRICING[model]["input"] == 5.00
        assert config.PRICING[model]["output"] == 25.00


def test_mantle_url_has_region():
    assert config.MANTLE_URL == "https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages"


def test_defaults():
    assert config.DEFAULT_RUNS == 5
    assert config.BEDROCK_REGION == "us-east-1"
    assert config.INTER_CALL_DELAY_S == 0.2
    assert config.RETRY_MAX_ATTEMPTS == 3


def test_model_key_from_id_opus_47():
    assert config.model_key_from_id("global.anthropic.claude-opus-4-7") == "opus-4.7"
    assert config.model_key_from_id("claude-opus-4-7") == "opus-4.7"


def test_model_key_from_id_opus_46():
    assert config.model_key_from_id("global.anthropic.claude-opus-4-6-v1") == "opus-4.6"
    assert config.model_key_from_id("claude-opus-4-6") == "opus-4.6"


def test_model_key_from_id_unknown_raises():
    with pytest.raises(ValueError, match="Unknown model id"):
        config.model_key_from_id("gpt-4")
