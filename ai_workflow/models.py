"""Data models shared across the AI workflow command modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiffFile:
    """A single changed file inside a diff."""

    path: str
    additions: int = 0
    deletions: int = 0
    content: str = ""


@dataclass
class DiffResult:
    """Parsed diff result for a repository or PR."""

    files: list[DiffFile] = field(default_factory=list)
    is_large: bool = False

    @property
    def total_additions(self) -> int:
        """Return the total number of added lines."""
        return sum(f.additions for f in self.files)

    @property
    def total_deletions(self) -> int:
        """Return the total number of deleted lines."""
        return sum(f.deletions for f in self.files)

    @property
    def total_lines(self) -> int:
        """Return the total number of diff lines."""
        return sum(len(f.content.splitlines()) for f in self.files)

    def is_empty(self) -> bool:
        """Return True when there are no files to inspect."""
        return not self.files


@dataclass
class TriageResult:
    """Structured result from AI issue triage."""

    labels: list[str] = field(default_factory=list)
    priority: str = "medium"
    complexity: str = "medium"
    is_duplicate: bool = False
    needs_more_info: bool = False
    summary: str = ""


@dataclass
class QualityCheck:
    """A single dimension score inside a quality report."""

    score: int = 0
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Multi-dimensional AI quality gate result."""

    overall_score: int = 0
    checks: dict[str, QualityCheck] = field(default_factory=dict)
    summary: str = ""
    threshold: int = 60

    @property
    def passed(self) -> bool:
        """Return True when the overall score meets the threshold."""
        return self.overall_score >= self.threshold


@dataclass
class CommitInfo:
    """Metadata about a single git commit."""

    hash: str
    message: str
    author: str
    date: str
    commit_type: str = ""
