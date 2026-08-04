"""Configuration management for NovusAutomata.

Configuration resolution order:
    1. Environment variables (highest priority)
    2. Configuration file (JSON/YAML) at --config or ~/.novusautomata/config
    3. Built-in defaults (lowest priority)
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    """Read an environment variable with a default value."""
    return os.environ.get(key, default)


@dataclass
class Config:
    """Runtime configuration for all AI workflow commands."""

    # AI Provider
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_timeout: int = 180
    nvidia_retry_count: int = 3
    nvidia_retry_delay: float = 2.0

    # Model routing
    model_review: str = "deepseek-ai/deepseek-v4-pro"
    model_fix: str = "deepseek-ai/deepseek-v4-flash"
    model_triage: str = "nvidia/nemotron-3-super-120b-a12b"
    model_quality: str = "deepseek-ai/deepseek-v4-pro"
    model_changelog: str = "deepseek-ai/deepseek-v4-flash"
    model_summary: str = "deepseek-ai/deepseek-v4-flash"
    model_security: str = "deepseek-ai/deepseek-v4-pro"
    model_commitlint: str = "nvidia/nemotron-3-super-120b-a12b"
    model_generic: str = "deepseek-ai/deepseek-v4-flash"

    # Git
    git_user_name: str = "novus-automata[bot]"
    git_user_email: str = "bot@novusautomata.dev"

    # Safety
    protected_paths: list[str] = field(
        default_factory=lambda: [
            ".github/",
            ".git/",
            ".env",
            "secret",
            "credential",
            "token",
            "password",
            "*.pem",
            "*.key",
            "auth/",
        ]
    )
    max_diff_size: int = 2000
    max_file_size: int = 1_048_576
    max_files_per_batch: int = 20
    max_fix_retries: int = 2

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Environment variable name overrides
    _ENV_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "nvidia_api_key": "NVIDIA_API_KEY",
            "nvidia_base_url": "NVIDIA_BASE_URL",
            "nvidia_timeout": "NVIDIA_TIMEOUT",
            "nvidia_retry_count": "NVIDIA_RETRY_COUNT",
            "nvidia_retry_delay": "NVIDIA_RETRY_DELAY",
            "model_review": "NVIDIA_REVIEW_MODEL",
            "model_fix": "NVIDIA_FIX_MODEL",
            "model_triage": "NVIDIA_TRIAGE_MODEL",
            "model_quality": "NVIDIA_QUALITY_MODEL",
            "model_changelog": "NVIDIA_CHANGELOG_MODEL",
            "model_summary": "NVIDIA_SUMMARY_MODEL",
            "model_security": "NVIDIA_SECURITY_MODEL",
            "model_commitlint": "NVIDIA_COMMITLINT_MODEL",
            "model_generic": "NVIDIA_GENERIC_MODEL",
            "git_user_name": "GIT_USER_NAME",
            "git_user_email": "GIT_USER_EMAIL",
            "log_level": "LOG_LEVEL",
            "max_diff_size": "MAX_DIFF_SIZE",
            "max_file_size": "MAX_FILE_SIZE",
            "max_files_per_batch": "MAX_FILES_PER_BATCH",
            "max_fix_retries": "MAX_FIX_RETRIES",
        },
        init=False,
        repr=False,
    )
    _INT_FIELDS: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "nvidia_timeout",
                "nvidia_retry_count",
                "max_diff_size",
                "max_file_size",
                "max_files_per_batch",
                "max_fix_retries",
            }
        ),
        init=False,
        repr=False,
    )
    _FLOAT_FIELDS: frozenset[str] = field(
        default_factory=lambda: frozenset({"nvidia_retry_delay"}),
        init=False,
        repr=False,
    )

    def apply_env(self) -> None:
        """Override config values from environment variables."""
        for field_name, env_name in self._ENV_MAP.items():
            raw = _env(env_name)
            if raw == "":
                continue
            if field_name in self._INT_FIELDS:
                try:
                    setattr(self, field_name, int(raw))
                except ValueError:
                    continue
            elif field_name in self._FLOAT_FIELDS:
                try:
                    setattr(self, field_name, float(raw))
                except ValueError:
                    continue
            else:
                setattr(self, field_name, raw)

    def load_file(self, path: str | None = None) -> None:
        """Load configuration from a JSON file (if present)."""
        config_path = path or _env("NOVUSAUTOMATA_CONFIG")
        if not config_path:
            config_path = str(pathlib.Path.home() / ".novusautomata" / "config.json")
        if not os.path.isfile(config_path):
            return
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for key, value in data.items():
            if hasattr(self, key) and key not in {"_ENV_MAP", "_INT_FIELDS", "_FLOAT_FIELDS"}:
                setattr(self, key, value)

    def require_api_key(self) -> str:
        """Return the API key or raise a clear error."""
        if not self.nvidia_api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. Set it in the environment or "
                "in ~/.novusautomata/config.json"
            )
        return self.nvidia_api_key


def load_config() -> Config:
    """Load configuration from file and environment, returning a Config."""
    config = Config()
    config.load_file()
    config.apply_env()
    return config
