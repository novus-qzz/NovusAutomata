"""Tests for AI workflow commands."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

from ai_workflow.commands import (
    commitlint,
    health,
    respond,
    review,
    securix,
    simplify,
    stale,
    welcome,
)
from ai_workflow.config import Config
from ai_workflow.gh_utils import GHError


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


class TestReviewCommand:
    """Tests for the review command."""

    @patch("ai_workflow.commands.review.GHClient")
    def test_review_no_diff(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.pr_diff.return_value = ""
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai()
        args = _make_args(pr_number=1)
        result = review.run(args, config, ai)
        assert result == 0

    @patch("ai_workflow.commands.review.GHClient")
    def test_review_success(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.pr_diff.return_value = "diff --git a/test.py b/test.py\n+line1\n+line2"
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai("No issues found. Looks good!")
        args = _make_args(pr_number=1)
        result = review.run(args, config, ai)
        assert result == 0
        mock_gh.pr_review.assert_called_once()

    @patch("ai_workflow.commands.review.GHClient")
    def test_review_with_issues(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.pr_diff.return_value = "diff --git a/test.py b/test.py\n+line1"
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai("- File: test.py | Line: 1 | Severity: WARNING\n  Issue: test")
        args = _make_args(pr_number=1)
        result = review.run(args, config, ai)
        assert result == 0

    @patch("ai_workflow.commands.review.GHClient")
    def test_review_no_issues_found(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.pr_diff.return_value = "diff --git a/test.py b/test.py\n+line1"
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai("NO_ISSUES_FOUND")
        args = _make_args(pr_number=1)
        result = review.run(args, config, ai)
        assert result == 0


class TestRespondCommand:
    """Tests for the respond command."""

    @patch("ai_workflow.commands.respond.GHClient")
    def test_respond_no_issue(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.issue_view.side_effect = GHError("not found")
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai()
        args = _make_args(issue_number=1, comment="test comment")
        result = respond.run(args, config, ai)
        assert result == 1

    @patch("ai_workflow.commands.respond.GHClient")
    def test_respond_success(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.issue_view.return_value = {"title": "Test Issue"}
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai("Thanks for your comment!")
        args = _make_args(issue_number=1, comment="test comment")
        result = respond.run(args, config, ai)
        assert result == 0
        mock_gh.issue_comment.assert_called_once()


class TestSimplifyCommand:
    """Tests for the simplify command."""

    @patch("ai_workflow.commands.simplify.GitRepo")
    def test_simplify_no_repo(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = False
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = simplify.run(_make_args(), config, ai)
        assert result == 1

    @patch("ai_workflow.commands.simplify.GitRepo")
    def test_simplify_no_diff(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo.diff.return_value.is_empty.return_value = True
        mock_repo.diff.return_value.files = []
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = simplify.run(_make_args(), config, ai)
        assert result == 0

    @patch("ai_workflow.commands.simplify.GitRepo")
    def test_simplify_with_diff(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_file = MagicMock()
        mock_file.content = "if x == True:\n    pass\n"
        mock_repo.diff.return_value.files = [mock_file]
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai("Suggestion: Replace `if x == True:` with `if x:`")
        result = simplify.run(_make_args(), config, ai)
        assert result == 0


class TestHealthCommand:
    """Tests for the health command."""

    @patch("ai_workflow.commands.health.GitRepo")
    def test_health_no_repo(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = False
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = health.run(_make_args(), config, ai)
        assert result == 1

    @patch("ai_workflow.commands.health.GitRepo")
    def test_health_success(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_commit = MagicMock()
        mock_commit.message = "feat: add feature"
        mock_commit.author = "test"
        mock_repo.log.return_value = [mock_commit]
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai("## Health Report\nScore: 85/100")
        result = health.run(_make_args(), config, ai)
        assert result == 0


class TestWelcomeCommand:
    """Tests for the welcome command."""

    @patch("ai_workflow.commands.welcome.GHClient")
    def test_welcome_not_first_time(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.user_is_first_time.return_value = False
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai()
        args = _make_args(username="experienceduser")
        result = welcome.run(args, config, ai)
        assert result == 0
        ai.chat.assert_not_called()

    @patch("ai_workflow.commands.welcome.GHClient")
    def test_welcome_first_time(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.user_is_first_time.return_value = True
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai("Welcome to the project!")
        args = _make_args(username="newuser")
        result = welcome.run(args, config, ai)
        assert result == 0
        ai.chat.assert_called_once()


class TestCommitlintCommand:
    """Tests for the commitlint command."""

    @patch("ai_workflow.commands.commitlint.GitRepo")
    def test_commitlint_no_repo(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = False
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = commitlint.run(_make_args(), config, ai)
        assert result == 1

    @patch("ai_workflow.commands.commitlint.GitRepo")
    def test_commitlint_valid(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_commit = MagicMock()
        mock_commit.hash = "abc123456"
        mock_commit.message = "feat: add new feature"
        mock_repo.log.return_value = [mock_commit]
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = commitlint.run(_make_args(), config, ai)
        assert result == 0

    @patch("ai_workflow.commands.commitlint.GitRepo")
    def test_commitlint_invalid(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_commit = MagicMock()
        mock_commit.hash = "abc123456"
        mock_commit.message = "bad message"
        mock_repo.log.return_value = [mock_commit]
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = commitlint.run(_make_args(), config, ai)
        assert result == 1


class TestStaleCommand:
    """Tests for the stale command."""

    @patch("ai_workflow.commands.stale.GHClient")
    def test_stale_no_issues(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.issue_list.return_value = []
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai()
        result = stale.run(_make_args(days=30), config, ai)
        assert result == 0

    @patch("ai_workflow.commands.stale.GHClient")
    def test_stale_with_old_issue(self, mock_gh_cls: MagicMock) -> None:
        mock_gh = MagicMock()
        mock_gh.issue_list.return_value = [
            {
                "number": 1,
                "title": "Old Issue",
                "labels": [{"name": "question"}],
                "updatedAt": "2024-01-01T00:00:00Z",
            }
        ]
        mock_gh_cls.return_value = mock_gh
        config = _make_config()
        ai = _make_ai()
        result = stale.run(_make_args(days=30), config, ai)
        assert result == 0
        mock_gh.issue_edit.assert_called_once()


class TestSecurixCommand:
    """Tests for the securix command."""

    @patch("ai_workflow.commands.securix.GitRepo")
    def test_securix_no_report(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo.diff.return_value.files = []
        mock_repo_cls.return_value = mock_repo
        config = _make_config()
        ai = _make_ai()
        result = securix.run(_make_args(report=""), config, ai)
        assert result == 0

    @patch("ai_workflow.commands.securix.GitRepo")
    @patch("ai_workflow.commands.securix.SafeFileWriter")
    @patch("builtins.open", create=True)
    def test_securix_with_report(
        self, mock_open: MagicMock, mock_writer_cls: MagicMock, mock_repo_cls: MagicMock
    ) -> None:
        mock_repo = MagicMock()
        mock_repo.is_repo.return_value = True
        mock_repo_cls.return_value = mock_repo
        mock_writer = MagicMock()
        mock_writer.write_batch.return_value = 1
        mock_writer_cls.return_value = mock_writer
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "Fix CVE-2024-1234"
        config = _make_config()
        ai = _make_ai("===FILE:test.py===\nfixed content\n===END===")
        result = securix.run(_make_args(report="report.json"), config, ai)
        assert result == 0
