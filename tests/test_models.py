"""Tests for data models."""

from __future__ import annotations

from ai_workflow.models import (
    CommitInfo,
    DiffFile,
    DiffResult,
    QualityCheck,
    QualityReport,
    TriageResult,
)


def test_diff_file_defaults() -> None:
    f = DiffFile(path="test.py")
    assert f.path == "test.py"
    assert f.additions == 0
    assert f.deletions == 0
    assert f.content == ""


def test_diff_file_with_values() -> None:
    f = DiffFile(path="a.py", additions=10, deletions=5, content="line1\nline2\n")
    assert f.additions == 10
    assert f.deletions == 5


def test_diff_result_empty() -> None:
    r = DiffResult()
    assert r.is_empty()
    assert r.total_additions == 0
    assert r.total_deletions == 0
    assert r.total_lines == 0


def test_diff_result_with_files() -> None:
    files = [
        DiffFile(path="a.py", additions=5, deletions=2, content="a\nb\n"),
        DiffFile(path="b.py", additions=3, deletions=1, content="c\n"),
    ]
    r = DiffResult(files=files)
    assert not r.is_empty()
    assert r.total_additions == 8
    assert r.total_deletions == 3
    assert r.total_lines == 3


def test_triage_result_defaults() -> None:
    t = TriageResult()
    assert t.labels == []
    assert t.priority == "medium"
    assert t.complexity == "medium"
    assert t.is_duplicate is False
    assert t.needs_more_info is False
    assert t.summary == ""


def test_triage_result_with_values() -> None:
    t = TriageResult(
        labels=["bug", "high-priority"],
        priority="high",
        complexity="low",
        is_duplicate=True,
        needs_more_info=True,
        summary="Test issue",
    )
    assert t.labels == ["bug", "high-priority"]
    assert t.priority == "high"
    assert t.is_duplicate is True


def test_quality_check_defaults() -> None:
    q = QualityCheck()
    assert q.score == 0
    assert q.issues == []


def test_quality_report_defaults() -> None:
    r = QualityReport()
    assert r.overall_score == 0
    assert r.checks == {}
    assert r.summary == ""
    assert r.threshold == 60
    assert not r.passed


def test_quality_report_passed() -> None:
    r = QualityReport(overall_score=75, threshold=60)
    assert r.passed


def test_quality_report_failed() -> None:
    r = QualityReport(overall_score=40, threshold=60)
    assert not r.passed


def test_commit_info_defaults() -> None:
    c = CommitInfo(hash="abc123", message="test", author="user", date="2024-01-01")
    assert c.hash == "abc123"
    assert c.message == "test"
    assert c.author == "user"
    assert c.date == "2024-01-01"
    assert c.commit_type == ""
