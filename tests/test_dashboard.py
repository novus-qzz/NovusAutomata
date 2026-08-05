"""Tests for dashboard command — CI dashboard rendering."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

from ai_workflow.commands.dashboard import (
    _colorize,
    _format_duration,
    _format_timestamp,
    _table,
)


def test_format_duration_seconds() -> None:
    assert _format_duration(30) == "30s"


def test_format_duration_minutes() -> None:
    assert _format_duration(120) == "2m0s"
    assert _format_duration(155) == "2m35s"


def test_format_timestamp() -> None:
    ts = "2026-08-05T01:20:00Z"
    result = _format_timestamp(ts)
    assert "2026-08-05" in result
    assert "01:20:00" in result


def test_format_timestamp_invalid() -> None:
    result = _format_timestamp("not-a-date")
    assert result == "not-a-date"


def test_table_basic() -> None:
    headers = ["A", "B", "C"]
    rows = [["1", "2", "3"], ["4", "5", "6"]]
    table = _table(headers, rows)
    assert "A" in table
    assert "B" in table
    assert "C" in table
    assert "1" in table
    assert "4" in table


def test_table_empty_rows() -> None:
    headers = ["X", "Y"]
    table = _table(headers, [])
    assert "X" in table
    assert "Y" in table


def test_table_widths_override() -> None:
    headers = ["Name", "Status"]
    rows = [["short", "ok"]]
    table = _table(headers, rows, widths=[20, 10])
    # The table should respect the width override
    assert len(table.split("\n")) >= 4  # at least header + separator + row + separator


def test_colorize() -> None:
    result = _colorize("success", "pass")
    assert "pass" in result
    assert "\033[32m" in result  # green for success

    result_fail = _colorize("failure", "fail")
    assert "fail" in result_fail
    assert "\033[31m" in result_fail  # red for failure


def test_colorize_unknown_status() -> None:
    result = _colorize("unknown", "test")
    assert "test" in result


@patch("ai_workflow.commands.dashboard._fetch_runs")
def test_dashboard_no_runs(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = []
    args = argparse.Namespace(branch="main", limit=10)

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        from ai_workflow.commands.dashboard import _run_dashboard

        _run_dashboard(args)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "No runs found" in output


@patch("ai_workflow.commands.dashboard._fetch_runs")
def test_dashboard_runs(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [
        {
            "name": "Test Workflow",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "event": "push",
            "display_title": "test run",
            "run_started_at": 0,
            "created_at": 0,
            "updated_at": "2026-08-05T01:20:00Z",
        }
    ]
    args = argparse.Namespace(branch="main", limit=5)

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        from ai_workflow.commands.dashboard import _run_dashboard

        _run_dashboard(args)
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "CI Dashboard" in output
    assert "Test Workflow" in output
