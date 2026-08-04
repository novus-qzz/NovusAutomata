"""Tests for the configuration module."""

from __future__ import annotations

import pytest

from ai_workflow.config import Config


def test_defaults() -> None:
    config = Config()
    assert config.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert config.model_review.startswith("deepseek")
    assert config.nvidia_retry_count == 3
    assert ".github/" in config.protected_paths


def test_require_api_key_raises_when_missing() -> None:
    config = Config()
    config.nvidia_api_key = ""
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
        config.require_api_key()


def test_apply_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_BASE_URL", "http://localhost:8080/v1")
    monkeypatch.setenv("NVIDIA_RETRY_COUNT", "5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    config = Config()
    config.apply_env()
    assert config.nvidia_base_url == "http://localhost:8080/v1"
    assert config.nvidia_retry_count == 5
    assert config.log_level == "DEBUG"
