"""Tests for the new AI workflow commands."""

from __future__ import annotations

import argparse
import json
import pathlib
from unittest.mock import MagicMock, patch

from ai_workflow.commands import audit, diff, plan, status
from ai_workflow.config import Config


def _make_config() -> Config:
    config = Config()
    config.nvidia_api_key = "test-key"
    return config


def _make_args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _make_ai(*responses: str) -> MagicMock:
    ai = MagicMock()
    ai.chat.side_effect = list(responses)
    return ai


class TestAuditCommand:
    """Tests for the audit command."""

    def test_audit_no_report(self) -> None:
        config = _make_config()
        ai = _make_ai()
        args = _make_args(report="")
        result = audit.run(args, config, ai)
        assert result == 1

    def test_audit_valid_report(self, tmp_path: pathlib.Path) -> None:
        report = tmp_path / "audit.json"
        report.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {
                            "name": "flask",
                            "version": "1.0.0",
                            "vulns": [
                                {
                                    "id": "CVE-2023-1234",
                                    "severity": "HIGH",
                                    "aliases": ["CVE-2023-1234"],
                                }
                            ],
                        },
                        {
                            "name": "requests",
                            "version": "2.0.0",
                            "vulns": [],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        config = _make_config()
        ai = _make_ai("## Report\n- flask 1.0.0 | HIGH | CVE-2023-1234")
        args = _make_args(report=str(report))
        result = audit.run(args, config, ai)
        assert result == 0
        ai.chat.assert_called_once()


class TestDiffCommand:
    """Tests for the diff command."""

    @patch("ai_workflow.commands.diff.GitRepo")
    def test_diff_clean(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo.diff.return_value.is_empty.return_value = True
        mock_repo.diff.return_value.total_additions = 0
        mock_repo.diff.return_value.total_deletions = 0
        mock_repo.diff.return_value.files = []
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = diff.run(_make_args(), config, ai)
        assert result == 0

    @patch("ai_workflow.commands.diff.GitRepo")
    def test_diff_has_changes(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_result = MagicMock()
        mock_result.is_empty.return_value = False
        mock_result.total_additions = 5
        mock_result.total_deletions = 3
        mock_result.files = [MagicMock(path="app.py", additions=5, deletions=3, content="")]
        mock_repo.diff.return_value = mock_result
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = diff.run(_make_args(), config, ai)
        assert result == 0


class TestPlanCommand:
    """Tests for the plan command."""

    @patch("ai_workflow.commands.plan.GitRepo")
    def test_plan_no_goal_no_diff(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_result = MagicMock()
        mock_result.is_empty.return_value = True
        mock_repo.diff.return_value = mock_result
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        args = _make_args(goal="")
        result = plan.run(args, config, ai)
        assert result == 1

    @patch("ai_workflow.commands.plan.GitRepo")
    def test_plan_with_goal(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai("## Plan\n- Step 1\n- Step 2")
        args = _make_args(goal="Add health endpoint")
        result = plan.run(args, config, ai)
        assert result == 0
        ai.chat.assert_called_once()


class TestStatusCommand:
    """Tests for the status command."""

    @patch("ai_workflow.commands.status.GitRepo")
    def test_status(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo.current_branch.return_value = "main"
        mock_repo.is_clean.return_value = True
        mock_repo.status.return_value = ""
        mock_repo.log.return_value = [MagicMock(hash="abc123", message="init", author="test")]
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = status.run(_make_args(), config, ai)
        assert result == 0
