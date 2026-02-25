"""config.py 유닛 테스트."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from bot.config import BotConfig, load_config


@pytest.fixture
def env_vars():
    """최소 필수 환경 변수."""
    return {
        "TELEGRAM_BOT_TOKEN": "test-token-123",
        "TELEGRAM_USER_IDS": "111,222",
    }


class TestLoadConfig:
    def test_loads_required_vars(self, env_vars):
        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()
        assert config.telegram_bot_token == "test-token-123"
        assert config.allowed_user_ids == [111, 222]
        assert isinstance(config.project_root, Path)

    def test_missing_token_raises(self):
        with patch.dict(os.environ, {"TELEGRAM_USER_IDS": "123"}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
                load_config()

    def test_missing_user_ids_raises(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_USER_IDS"):
                load_config()

    def test_defaults(self, env_vars):
        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()
        assert config.default_model == "sonnet"
        assert config.claude_timeout == 300
        assert config.max_turns == 10
        assert config.max_budget_usd == 2.0
        assert config.log_level == "INFO"

    def test_custom_values(self, env_vars):
        env_vars.update({
            "DEFAULT_MODEL": "opus",
            "CLAUDE_TIMEOUT": "600",
            "MAX_TURNS": "20",
            "MAX_BUDGET_USD": "5.00",
            "LOG_LEVEL": "DEBUG",
        })
        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()
        assert config.default_model == "opus"
        assert config.claude_timeout == 600
        assert config.max_turns == 20
        assert config.max_budget_usd == 5.0
        assert config.log_level == "DEBUG"

    def test_single_user_id(self):
        env = {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_USER_IDS": "999"}
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
        assert config.allowed_user_ids == [999]
