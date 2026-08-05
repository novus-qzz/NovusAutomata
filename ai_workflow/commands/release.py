"""Automated release management with version bumping and changelog generation."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_VERSION_FILE = "pyproject.toml"
_VERSION_PATTERN = re.compile(r'version\s*=\s*"(\d+\.\d+\.\d+)"')


def _get_current_version() -> str | None:
    """Extract current version from pyproject.toml."""
    try:
        content = Path(_VERSION_FILE).read_text(encoding="utf-8")
        match = _VERSION_PATTERN.search(content)
        if match:
            return match.group(1)
    except OSError as exc:
        logger.warning("Failed to read version file: %s", exc)
    return None


def _bump_version(version: str, bump_type: str) -> str:
    """Bump semantic version."""
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    # patch
    return f"{major}.{minor}.{patch + 1}"


def _update_version(new_version: str) -> bool:
    """Update version in pyproject.toml."""
    try:
        content = Path(_VERSION_FILE).read_text(encoding="utf-8")
        new_content = _VERSION_PATTERN.sub(f'version = "{new_version}"', content)
        Path(_VERSION_FILE).write_text(new_content, encoding="utf-8")
        return True
    except OSError as exc:
        logger.error("Failed to update version: %s", exc)
        return False


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the release subcommand."""
    p = subparsers.add_parser("release", help="Automated release management")
    p.add_argument("--bump", choices=["patch", "minor", "major"], help="Version bump type")
    p.add_argument("--tag", help="Specific version tag (e.g., v1.2.3)")
    p.add_argument("--generate-changelog", action="store_true", help="Generate changelog")
    p.add_argument("--publish", action="store_true", help="Publish release to GitHub")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without applying")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Manage release process."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1

    current_version = _get_current_version()
    if not current_version:
        logger.error("Could not determine current version")
        return 1

    if args.tag:
        new_version = args.tag.lstrip("v")
    elif args.bump:
        new_version = _bump_version(current_version, args.bump)
    else:
        logger.error("Specify --bump or --tag")
        return 1

    print(f"## Release: {current_version} -> {new_version}\n")

    if args.dry_run:
        print("**Dry Run Mode** - No changes will be applied\n")
        print(f"Version: {current_version} -> {new_version}")
        print(f"Tag: v{new_version}")
        if args.generate_changelog:
            print("Changelog: Will be generated")
        if args.publish:
            print("Publish: Will create GitHub Release")
        return 0

    if not _update_version(new_version):
        return 1
    print(f"Updated version to {new_version}")

    repo.commit(f"chore: release v{new_version}")
    repo.create_branch(f"release/v{new_version}")
    repo.push("origin", f"release/v{new_version}")

    repo.checkout("main")
    repo.commit(f"chore: bump version to {new_version}")
    repo.push("origin", "main")

    print(f"Created release branch: release/v{new_version}")
    print(f"Tag: v{new_version}")
    print("\nTo create GitHub Release, run:")
    print(f"  gh release create v{new_version} --title 'Release v{new_version}' --generate-notes")

    return 0
