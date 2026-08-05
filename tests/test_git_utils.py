"""Tests for git utilities."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ai_workflow.git_utils import GitError, GitRepo


def test_git_repo_init() -> None:
    repo = GitRepo(cwd="/tmp", timeout=10)
    assert repo._cwd == "/tmp"
    assert repo._timeout == 10


def test_git_repo_default() -> None:
    repo = GitRepo()
    assert repo._cwd is None
    assert repo._timeout == 30


@patch("ai_workflow.git_utils.subprocess.run")
def test_git_repo_run_success(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "output"
    mock_run.return_value = mock_proc

    repo = GitRepo()
    result = repo._run("status")
    assert result == "output"


@patch("ai_workflow.git_utils.subprocess.run")
def test_git_repo_run_failure(mock_run: MagicMock) -> None:
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "fatal: not a git repository"
    mock_run.return_value = mock_proc

    repo = GitRepo()
    with pytest.raises(GitError, match="failed"):
        repo._run("status")


@patch("ai_workflow.git_utils.subprocess.run")
def test_git_repo_run_injection_rejected(mock_run: MagicMock) -> None:
    repo = GitRepo()
    with pytest.raises(GitError, match="unsafe"):
        repo._run("log", "--since=2024-01-01; rm -rf /")


@patch("ai_workflow.git_utils.subprocess.run")
def test_git_repo_run_timeout(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git"], timeout=30)

    repo = GitRepo()
    with pytest.raises(GitError, match="timed out"):
        repo._run("status")


@patch("ai_workflow.git_utils.subprocess.run")
def test_git_repo_run_file_not_found(mock_run: MagicMock) -> None:
    mock_run.side_effect = FileNotFoundError()

    repo = GitRepo()
    with pytest.raises(GitError, match="not found"):
        repo._run("status")


@patch.object(GitRepo, "_run")
def test_git_repo_is_repo_true(mock_run: MagicMock) -> None:
    mock_run.return_value = "true\n"
    repo = GitRepo()
    assert repo.is_repo() is True


@patch.object(GitRepo, "_run")
def test_git_repo_is_repo_false(mock_run: MagicMock) -> None:
    mock_run.side_effect = GitError("not a repo")
    repo = GitRepo()
    assert repo.is_repo() is False


@patch.object(GitRepo, "_run")
def test_git_repo_current_branch(mock_run: MagicMock) -> None:
    mock_run.return_value = "main\n"
    repo = GitRepo()
    assert repo.current_branch() == "main"


@patch.object(GitRepo, "_run")
def test_git_repo_is_clean_true(mock_run: MagicMock) -> None:
    mock_run.return_value = ""
    repo = GitRepo()
    assert repo.is_clean() is True


@patch.object(GitRepo, "_run")
def test_git_repo_is_clean_false(mock_run: MagicMock) -> None:
    mock_run.return_value = " M file.py"
    repo = GitRepo()
    assert repo.is_clean() is False


@patch.object(GitRepo, "_run")
def test_git_repo_status(mock_run: MagicMock) -> None:
    mock_run.return_value = " M file.py\n?? new.py\n"
    repo = GitRepo()
    result = repo.status()
    assert "file.py" in result


@patch.object(GitRepo, "_run")
def test_git_repo_diff_empty(mock_run: MagicMock) -> None:
    mock_run.return_value = ""
    repo = GitRepo()
    result = repo.diff()
    assert result.is_empty()


@patch.object(GitRepo, "_run")
def test_git_repo_diff_with_files(mock_run: MagicMock) -> None:
    numstat = "5\t3\tfile.py\n10\t0\tnew.py\n"
    diff_output = "diff --git a/file.py b/file.py\nline1\nline2\n"
    mock_run.side_effect = [numstat, diff_output]
    repo = GitRepo()
    result = repo.diff()
    assert len(result.files) == 2
    assert result.total_additions == 15
    assert result.total_deletions == 3


@patch.object(GitRepo, "_run")
def test_git_repo_log(mock_run: MagicMock) -> None:
    mock_run.return_value = "abc123\tAuthor\t2024-01-01\tInitial commit\n"
    repo = GitRepo()
    commits = repo.log()
    assert len(commits) == 1
    assert commits[0].hash == "abc123"
    assert commits[0].author == "Author"


@patch.object(GitRepo, "_run")
def test_git_repo_commit(mock_run: MagicMock) -> None:
    repo = GitRepo()
    result = repo.commit("test message")
    assert result is True
    assert mock_run.call_count == 2


@patch.object(GitRepo, "_run")
def test_git_repo_checkout(mock_run: MagicMock) -> None:
    repo = GitRepo()
    result = repo.checkout("main")
    assert result is True


@patch.object(GitRepo, "_run")
def test_git_repo_create_branch(mock_run: MagicMock) -> None:
    repo = GitRepo()
    result = repo.create_branch("feature")
    assert result is True


@patch.object(GitRepo, "_run")
def test_git_repo_push(mock_run: MagicMock) -> None:
    repo = GitRepo()
    result = repo.push()
    assert result is True


@patch.object(GitRepo, "_run")
def test_git_repo_tags(mock_run: MagicMock) -> None:
    mock_run.return_value = "v1.0\nv1.1\nv2.0\n"
    repo = GitRepo()
    tags = repo.tags()
    assert tags == ["v1.0", "v1.1", "v2.0"]


@patch.object(GitRepo, "_run")
def test_git_repo_tags_empty(mock_run: MagicMock) -> None:
    mock_run.return_value = ""
    repo = GitRepo()
    tags = repo.tags()
    assert tags == []
