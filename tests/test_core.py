"""Tests for core AI provider and utilities."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ai_workflow.config import Config
from ai_workflow.core import AIError, NVIDIAProvider, extract_json


def test_extract_json_plain() -> None:
    text = '{"key": "value"}'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_extract_json_with_code_fence() -> None:
    text = '```json\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_extract_json_with_prose() -> None:
    text = 'Here is the result:\n{"status": "ok"}\nDone.'
    result = extract_json(text)
    assert result == {"status": "ok"}


def test_extract_json_invalid() -> None:
    with pytest.raises(json.JSONDecodeError):
        extract_json("not json at all")


def test_extract_json_nested() -> None:
    text = '{"items": [1, 2, 3]}'
    result = extract_json(text)
    assert result["items"] == [1, 2, 3]


def test_nvidia_provider_name() -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    provider = NVIDIAProvider(config)
    assert provider.name() == "nvidia-nim"


def test_nvidia_provider_headers() -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    provider = NVIDIAProvider(config)
    headers = provider._headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


def test_nvidia_provider_payload() -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    provider = NVIDIAProvider(config)
    payload = provider._payload("system", "user", "model", 0.1, 100)
    data = json.loads(payload)
    assert data["model"] == "model"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "system"
    assert data["messages"][1]["role"] == "user"
    assert data["temperature"] == 0.1
    assert data["max_tokens"] == 100


@patch("ai_workflow.core.urllib.request.urlopen")
def test_nvidia_provider_chat_success(mock_urlopen: MagicMock) -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    provider = NVIDIAProvider(config)

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}]
    }).encode("utf-8")

    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_response)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_context

    result = provider.chat("system", "user")
    assert result == "Hello!"


@patch("ai_workflow.core.urllib.request.urlopen")
def test_nvidia_provider_chat_http_error(mock_urlopen: MagicMock) -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    config.nvidia_retry_count = 1
    provider = NVIDIAProvider(config)

    import urllib.error
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="", code=401, msg="Unauthorized", hdrs={}, fp=None
    )

    with pytest.raises(AIError, match="401"):
        provider.chat("system", "user")


@patch("ai_workflow.core.urllib.request.urlopen")
def test_nvidia_provider_chat_timeout(mock_urlopen: MagicMock) -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    config.nvidia_retry_count = 1
    provider = NVIDIAProvider(config)

    mock_urlopen.side_effect = TimeoutError("timeout")

    with pytest.raises(AIError, match="network"):
        provider.chat("system", "user")


@patch("ai_workflow.core.urllib.request.urlopen")
def test_nvidia_provider_chat_malformed_response(mock_urlopen: MagicMock) -> None:
    config = Config()
    config.nvidia_api_key = "test-key"
    config.nvidia_retry_count = 1
    provider = NVIDIAProvider(config)

    mock_response = MagicMock()
    mock_response.read.return_value = b"not json"

    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_response)
    mock_context.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_context

    with pytest.raises(AIError, match="malformed"):
        provider.chat("system", "user")
