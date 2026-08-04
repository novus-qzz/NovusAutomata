"""Shared pytest fixtures for the AI workflow test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_ai():
    """Return a deterministic fake AI provider."""

    class FakeAI:
        def __init__(self, responses: list[str] | None = None) -> None:
            self._responses = list(responses or [])
            self.calls: list[tuple[str, str]] = []

        def chat(self, system: str, user: str, model: str | None = None, **kwargs: object) -> str:
            self.calls.append((system, user))
            if self._responses:
                return self._responses.pop(0)
            return "mock response"

        def name(self) -> str:
            return "fake"

    return FakeAI
