"""Tests for GitHub utilities."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ai_workflow.gh_utils import GHClient, GHError


def test_gh_client_init() -> None:
    client = GHClient(timeout=30)
    assert client._timeout == 30


def test_gh_client_default_timeout() -> None:
    client = GHClient()
    assert client._timeout == 60


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_run_success(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "output"
    mock_run.return_value = mock_proc

    client = GHClient()
    result = client._run("pr", "list")
    assert result == "output"
    mock_run.assert_called_once()


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_run_failure(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "error message"
    mock_run.return_value = mock_proc

    client = GHClient()
    with pytest.raises(GHError, match="failed"):
        client._run("pr", "list")


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_run_timeout(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gh"], timeout=60)

    client = GHClient()
    with pytest.raises(GHError, match="timed out"):
        client._run("pr", "list")


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_run_file_not_found(mock_run: MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError()

    client = GHClient()
    with pytest.raises(GHError, match="not found"):
        client._run("pr", "list")


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_json_success(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '{"key": "value"}'
    mock_run.return_value = mock_proc

    client = GHClient()
    result = client._json("pr", "view", "1")
    assert result == {"key": "value"}


@patch("ai_workflow.gh_utils.subprocess.run")
def test_gh_client_json_invalid(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "not json"
    mock_run.return_value = mock_proc

    client = GHClient()
    result = client._json("pr", "view", "1")
    assert result == {}


@patch.object(GHClient, "_run")
def test_gh_client_pr_view(mock_run: MagicMock) -> None:
    mock_run.return_value = '{"title": "Test PR"}'
    client = GHClient()
    result = client.pr_view(1)
    assert result == {"title": "Test PR"}
    mock_run.assert_called_once()


@patch.object(GHClient, "_run")
def test_gh_client_pr_diff(mock_run: MagicMock) -> None:
    mock_run.return_value = "diff --git a/test.py b/test.py"
    client = GHClient()
    result = client.pr_diff(1)
    assert "diff" in result


@patch.object(GHClient, "_run")
def test_gh_client_pr_review(mock_run: MagicMock) -> None:
    client = GHClient()
    client.pr_review(1, "Looks good!")
    mock_run.assert_called_once()


@patch.object(GHClient, "_run")
def test_gh_client_issue_view(mock_run: MagicMock) -> None:
    mock_run.return_value = '{"title": "Bug report"}'
    client = GHClient()
    result = client.issue_view(1)
    assert result == {"title": "Bug report"}


@patch.object(GHClient, "_run")
def test_gh_client_issue_comment(mock_run: MagicMock) -> None:
    client = GHClient()
    client.issue_comment(1, "Thanks!")
    mock_run.assert_called_once()


@patch.object(GHClient, "_run")
def test_gh_client_issue_edit(mock_run: MagicMock) -> None:
    client = GHClient()
    client.issue_edit(1, add_labels=["bug", "urgent"])
    mock_run.assert_called_once()


@patch.object(GHClient, "_run")
def test_gh_client_issue_list(mock_run: MagicMock) -> None:
    mock_run.return_value = '[{"number": 1}, {"number": 2}]'
    client = GHClient()
    result = client.issue_list()
    assert len(result) == 2


@patch.object(GHClient, "_run")
def test_gh_client_repo_full_name(mock_run: MagicMock) -> None:
    mock_run.return_value = "owner/repo"
    client = GHClient()
    result = client.repo_full_name()
    assert result == "owner/repo"


@patch.object(GHClient, "_run")
def test_gh_client_user_is_first_time_true(mock_run: MagicMock) -> None:
    mock_run.return_value = "0"
    client = GHClient()
    assert client.user_is_first_time("newuser") is True


@patch.object(GHClient, "_run")
def test_gh_client_user_is_first_time_false(mock_run: MagicMock) -> None:
    mock_run.return_value = "5"
    client = GHClient()
    assert client.user_is_first_time("experienced") is False
