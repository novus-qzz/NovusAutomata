"""Safe file writing with path validation and atomic writes.

Protects against path traversal, writes to protected directories, symlink
attacks, oversized files, and batch-size abuse.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_workflow.config import Config

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".toml",
        ".cfg",
        ".ini",
        ".txt",
        ".sh",
        ".bat",
        ".ps1",
        ".html",
        ".css",
        ".scss",
        ".sql",
    }
)


class PathViolationError(Exception):
    """Raised when a path fails safety validation."""


class SafeFileWriter:
    """Validates paths and writes files atomically."""

    def __init__(self, config: Config) -> None:
        """Initialize with safety configuration."""
        self._config = config
        self._protected = []
        for p in config.protected_paths:
            if not p:
                continue
            stripped = p.strip("/\\")
            escaped = re.escape(stripped)
            if p.endswith(("/", "\\")):
                pattern = r"(^|[/\\])" + escaped + r"([/\\]|$|\.)"
            else:
                pattern = r"(^|[/\\]|\.)" + escaped
            self._protected.append(re.compile(pattern))

    def is_safe_path(self, path: str) -> bool:
        """Return True when a path is safe to write.

        Rejects:
            - Path traversal (``..`` components)
            - Absolute paths outside the repo
            - Protected patterns (secrets, credentials, dotfiles, etc.)
            - Symlink destinations
            - Disallowed file extensions
        """
        if not path or path.startswith("/") or "\\" in path:
            return False
        parts = path.split("/")
        if ".." in parts:
            return False
        resolved = Path(path).resolve()
        if resolved.is_symlink():
            return False
        for pattern in self._protected:
            if pattern.search(path):
                return False
        suffix = Path(path).suffix.lower()
        return suffix in _ALLOWED_EXTENSIONS

    def write(self, path: str, content: str) -> bool:
        """Write content to path if safe. Returns True on success."""
        if not self.is_safe_path(path):
            logger.warning("Skipping unsafe path: %s", path)
            return False
        if len(content.encode("utf-8")) > self._config.max_file_size:
            logger.warning("Skipping oversized file: %s", path)
            return False
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, target)
        except OSError as exc:
            logger.error("Failed to write %s: %s", path, exc)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False
        logger.debug("Wrote %s (%d bytes)", path, len(content.encode("utf-8")))
        return True

    def write_batch(self, files: dict[str, str]) -> int:
        """Write multiple files, returning the number written.

        Args:
            files: Mapping of path -> content.

        Returns:
            Count of successfully written files.
        """
        if len(files) > self._config.max_files_per_batch:
            logger.warning("Batch exceeds %d files, truncating", self._config.max_files_per_batch)
            files = dict(list(files.items())[: self._config.max_files_per_batch])
        written = 0
        for path, content in files.items():
            if self.write(path, content):
                written += 1
        return written
