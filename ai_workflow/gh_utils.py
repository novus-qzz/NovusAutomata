"""Safe wrapper around the GitHub CLI (``gh``)."""

from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


class GHError(Exception):
    """Raised when a GitHub CLI operation fails."""


class GHClient:
    """Wrapper around ``gh`` commands with structured error handling."""

    def __init__(self, timeout: int = 60) -> None:
        """Initialize the client with a per-command timeout."""
        self._timeout = timeout

    def _run(self, *args: str) -> str:
        """Run a gh command and return stdout, raising on failure."""
        try:
            result = subprocess.run(
                ["gh", *args],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GHError(
                "GitHub CLI (gh) not found. Install it from https://cli.github.com"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GHError(f"gh command timed out: {' '.join(args)}") from exc
        if result.returncode != 0:
            raise GHError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
        return result.stdout

    def _json(self, *args: str) -> dict[str, object]:
        """Run a gh command expecting JSON output."""
        output = self._run(*args)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {}

    # -- Pull requests ----------------------------------------------------

    def pr_view(self, pr_number: int) -> dict[str, object]:
        """Return PR metadata as a dict."""
        return self._json(
            "pr", "view", str(pr_number), "--json", "title,body,state,headRefName,baseRefName"
        )

    def pr_diff(self, pr_number: int) -> str:
        """Return the unified diff of a PR."""
        return self._run("pr", "diff", str(pr_number))

    def pr_review(self, pr_number: int, body: str, event: str = "COMMENT") -> None:
        """Submit a review comment on a PR."""
        self._run("pr", "review", str(pr_number), "--body", body, "--event", event)

    def pr_edit(self, pr_number: int, title: str | None = None, body: str | None = None) -> None:
        """Update a PR's title and/or body."""
        args = ["pr", "edit", str(pr_number)]
        if title:
            args.extend(["--title", title])
        if body:
            args.extend(["--body", body])
        self._run(*args)

    def pr_create(self, title: str, body: str, head: str, base: str = "main") -> str | None:
        """Create a PR and return its URL (or None)."""
        output = self._run(
            "pr", "create", "--title", title, "--body", body, "--head", head, "--base", base
        )
        return output.strip() or None

    def pr_list(self, state: str = "open", limit: int = 30) -> list[dict[str, object]]:
        """List PRs in a given state."""
        result = self._json(
            "pr", "list", "--state", state, "--limit", str(limit), "--json", "number,title,url"
        )
        return result if isinstance(result, list) else []

    # -- Issues -----------------------------------------------------------

    def issue_view(self, issue_number: int) -> dict[str, object]:
        """Return issue metadata as a dict."""
        return self._json(
            "issue",
            "view",
            str(issue_number),
            "--json",
            "title,body,state,labels",
        )

    def issue_comment(self, issue_number: int, body: str) -> None:
        """Post a comment on an issue."""
        self._run("issue", "comment", str(issue_number), "--body", body)

    def issue_edit(self, issue_number: int, add_labels: list[str] | None = None) -> None:
        """Add labels to an issue."""
        if add_labels:
            self._run("issue", "edit", str(issue_number), "--add-label", ",".join(add_labels))

    def issue_create(self, title: str, body: str, labels: list[str] | None = None) -> str | None:
        """Create an issue and return its URL (or None)."""
        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            args.extend(["--label", ",".join(labels)])
        output = self._run(*args)
        return output.strip() or None

    def issue_list(self, state: str = "open", limit: int = 50) -> list[dict[str, object]]:
        """List issues in a given state."""
        result = self._json(
            "issue",
            "list",
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,labels,updatedAt",
        )
        return result if isinstance(result, list) else []

    # -- Misc -------------------------------------------------------------

    def repo_full_name(self) -> str:
        """Return owner/repo for the current repository."""
        return self._run(
            "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
        ).strip()

    def user_is_first_time(self, username: str) -> bool:
        """Return True when the user has no merged PRs yet."""
        count = self._run(
            "search",
            "prs",
            f"author:{username} is:merged",
            "--json",
            "total_count",
            "--jq",
            ".total_count",
        ).strip()
        return count == "0" or count == ""
