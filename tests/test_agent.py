"""Tests for agent command — AI orchestrator."""

from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

from ai_workflow.commands.agent import (
    Step,
    _parse_plan,
    _run_one,
)
from ai_workflow.config import Config


def _make_config() -> Config:
    c = Config()
    c.nvidia_api_key = "test-key"
    return c


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_parse_plan_valid_json() -> None:
    text = json.dumps({
        "plan": [
            {"command": "review", "args": "--pr-number 123", "reason": "test"},
            {"command": "fix", "args": "--pr-number 123", "reason": "test"},
        ],
        "rationale": "Plan rationale",
    })
    result = _parse_plan(text)
    assert len(result) == 2
    assert result[0][0] == "review"
    assert result[0][1] == "--pr-number 123"


def test_parse_plan_invalid_command() -> None:
    text = json.dumps({
        "plan": [
            {"command": "nonexistent_cmd", "args": "", "reason": "bad"},
        ],
        "rationale": "",
    })
    result = _parse_plan(text)
    assert len(result) == 0


def test_parse_plan_invalid_json() -> None:
    result = _parse_plan("not valid json {{{")
    assert len(result) == 0


def test_step_dataclass() -> None:
    step = Step(command="review", args="--pr-number 1", reason="test step")
    assert step.status == "pending"
    assert step.output == ""
    assert step.error == ""
    assert step.elapsed == 0.0


@patch("ai_workflow.commands.agent.subprocess.run")
def test_run_one_success(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "some output"
    mock_proc.stderr = ""
    mock_run.return_value = mock_proc

    step = _run_one("review", "--pr-number 123", _make_config())
    assert step.status == "success"
    assert step.output == "some output"
    assert step.error == ""
    assert step.elapsed >= 0.0


@patch("ai_workflow.commands.agent.subprocess.run")
def test_run_one_failure(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "error message"
    mock_run.return_value = mock_proc

    step = _run_one("review", "--pr-number 123", _make_config())
    assert step.status == "failed"
    assert step.error == "error message"


@patch("ai_workflow.commands.agent.subprocess.run")
def test_run_one_timeout(mock_run: MagicMock) -> None:
    import subprocess as sp

    mock_run.side_effect = sp.TimeoutExpired(cmd=["python"], timeout=5)

    step = _run_one("review", "--pr-number 123", _make_config())
    assert step.status == "failed"
    assert "Timeout" in step.error
