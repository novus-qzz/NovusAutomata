"""Safe wrappers around git command-line operations.

All subprocess calls are parameterized (never ``shell=True``) and reject
command-injection characters in user-supplied inputs.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from ai_workflow.models import CommitInfo, DiffFile, DiffResult

logger = logging.getLogger(__name__)

_INJECTION_PATTERN = re.compile(r"[;&|`$]|\$\(|> /dev/")


class GitError(Exception):
    """Raised when a git operation fails."""


class GitRepo:
    """Thin, safe wrapper around git subprocess commands."""

    def __init__(self, cwd: str | None = None, timeout: int = 30) -> None:
        """Initialize the wrapper with an optional working directory."""
        self._cwd = cwd
        self._timeout = timeout

    def _run(self, *args: str) -> str:
        """Run a git command and return stdout, raising on failure."""
        for arg in args:
            if _INJECTION_PATTERN.search(arg):
                raise GitError(f"Rejected unsafe git argument: {arg!r}")
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitError("git executable not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"git command timed out: {' '.join(args)}") from exc
        if result.returncode != 0:
            raise GitError(f"git {args[0]} failed: {result.stderr.strip()}")
        return result.stdout

    def is_repo(self) -> bool:
        """Return True when the current directory is a git repository."""
        try:
            self._run("rev-parse", "--is-inside-work-tree")
            return True
        except GitError:
            return False

    def current_branch(self) -> str:
        """Return the current branch name."""
        return self._run("branch", "--show-current").strip()

    def is_clean(self) -> bool:
        """Return True when the working tree has no changes."""
        return self._run("status", "--porcelain").strip() == ""

    def status(self) -> str:
        """Return a porcelain status string."""
        return self._run("status", "--porcelain").strip()

    def diff(
        self,
        base_ref: str | None = None,
        exclude_paths: Sequence[str] | None = None,
    ) -> DiffResult:
        """Get a parsed diff against a base ref or the working tree.

        Args:
            base_ref: Optional ref to diff against. When None, diffs the
                working tree against HEAD.
            exclude_paths: Optional glob patterns to exclude.

        Returns:
            A structured DiffResult.
        """
        args: list[str] = ["diff", "--numstat"]
        if base_ref:
            args.append(base_ref)
        else:
            args.append("HEAD")
        if exclude_paths:
            args.extend(["--", *exclude_paths])
        numstat = self._run(*args)

        files: list[DiffFile] = []
        for line in numstat.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            additions, deletions, path = parts[0], parts[1], parts[2]
            if additions == "-" or deletions == "-":
                continue
            try:
                files.append(
                    DiffFile(
                        path=path,
                        additions=int(additions),
                        deletions=int(deletions),
                    )
                )
            except ValueError:
                continue

        if files:
            full = self._run("diff", *([base_ref] if base_ref else ["HEAD"]), "--", "-p")
            self._attach_contents(files, full)

        return DiffResult(files=files)

    def _attach_contents(self, files: list[DiffFile], full_diff: str) -> None:
        """Attach per-file hunks to each DiffFile from a unified diff."""
        current: DiffFile | None = None
        header_re = re.compile(r"^diff --git a/(.+?) b/.+$")
        for line in full_diff.splitlines():
            match = header_re.match(line)
            if match:
                path = match.group(1)
                current = next((f for f in files if f.path == path), None)
                continue
            if current is not None:
                current.content += line + "\n"

    def log(
        self,
        since: str | None = None,
        from_tag: str | None = None,
        to_tag: str | None = None,
        max_count: int = 50,
    ) -> list[CommitInfo]:
        """Return commit metadata matching the given filters."""
        args = [
            "log",
            "--format=%H%x09%an%x09%aI%x09%s",
            f"-{max_count}",
        ]
        if from_tag and to_tag:
            args.append(f"{from_tag}..{to_tag}")
        elif since:
            args.append(f"--since={since}")
        output = self._run(*args)
        commits: list[CommitInfo] = []
        for line in output.splitlines():
            parts = line.split("\t", 3)
            if len(parts) < 4:
                continue
            commits.append(
                CommitInfo(
                    hash=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3],
                )
            )
        return commits

    def commit(self, message: str) -> bool:
        """Create a commit with the given message. Returns True on success."""
        self._run("add", "-A")
        self._run("commit", "-m", message)
        return True

    def checkout(self, ref: str) -> bool:
        """Checkout a branch or commit."""
        self._run("checkout", ref)
        return True

    def create_branch(self, name: str) -> bool:
        """Create and switch to a new branch."""
        self._run("checkout", "-b", name)
        return True

    def push(self, remote: str = "origin", ref: str | None = None) -> bool:
        """Push the current or given ref to a remote."""
        args = ["push", remote]
        if ref:
            args.append(ref)
        self._run(*args)
        return True

    def tags(self, pattern: str | None = None) -> list[str]:
        """List tags matching an optional glob pattern."""
        args = ["tag", "--list"]
        if pattern:
            args.append(pattern)
        return [t for t in self._run(*args).splitlines() if t]
