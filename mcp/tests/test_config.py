"""Config loading: defaults, validation, and key handling.

No network, no secrets on disk. ``JIKEYAN_AGENT_KEY`` values used here are
obviously-fake placeholders.
"""

from __future__ import annotations

import pytest

from jikeyan_mcp.config import (
    DEFAULT_BASE_URL,
    Config,
    ConfigError,
    ENV_AGENT_KEY,
    ENV_BASE_URL,
    load_config,
)


def test_default_base_url_is_production() -> None:
    assert DEFAULT_BASE_URL == "https://api.jikeyan.cn"
    config = load_config({ENV_AGENT_KEY: "jk_test_placeholder"})
    assert isinstance(config, Config)
    assert config.base_url == "https://api.jikeyan.cn"
    assert config.api_root == "https://api.jikeyan.cn"


def test_missing_key_raises_without_echoing_anything() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config({})
    assert "JIKEYAN_AGENT_KEY" in str(excinfo.value)


def test_missing_key_message_contains_no_key_material() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config({ENV_AGENT_KEY: "   "})
    assert "jk_" not in str(excinfo.value)


def test_base_url_must_be_http() -> None:
    with pytest.raises(ConfigError):
        load_config({ENV_AGENT_KEY: "jk_test_placeholder", ENV_BASE_URL: "ftp://x"})
    with pytest.raises(ConfigError):
        load_config({ENV_AGENT_KEY: "jk_test_placeholder", ENV_BASE_URL: "   "})


def test_custom_base_url_is_accepted_and_normalized() -> None:
    config = load_config(
        {ENV_AGENT_KEY: "jk_test_placeholder", ENV_BASE_URL: "https://example.test/"}
    )
    assert config.api_root == "https://example.test"
