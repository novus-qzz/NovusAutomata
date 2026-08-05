"""Tests for safe file writer."""

from __future__ import annotations

import os
from pathlib import Path

from ai_workflow.config import Config
from ai_workflow.safe_io import SafeFileWriter


def test_safe_file_writer_init() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer._config == config


def test_safe_file_writer_is_safe_path_valid() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer.is_safe_path("test.py") is True
    assert writer.is_safe_path("src/main.py") is True
    assert writer.is_safe_path("README.md") is True


def test_safe_file_writer_is_safe_path_traversal() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer.is_safe_path("../secret.py") is False
    assert writer.is_safe_path("src/../../secret.py") is False


def test_safe_file_writer_is_safe_path_absolute() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer.is_safe_path("/etc/passwd") is False


def test_safe_file_writer_is_safe_path_protected() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer.is_safe_path(".env") is False
    assert writer.is_safe_path("secrets.json") is False
    assert writer.is_safe_path("credentials.yaml") is False
    assert writer.is_safe_path(".git/config") is False


def test_safe_file_writer_is_safe_path_extension() -> None:
    config = Config()
    writer = SafeFileWriter(config)
    assert writer.is_safe_path("image.png") is False
    assert writer.is_safe_path("archive.zip") is False
    assert writer.is_safe_path("binary.exe") is False


def test_safe_file_writer_write_success(tmp_path: Path) -> None:
    config = Config()
    writer = SafeFileWriter(config)
    # Use a relative path from tmp_path
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = writer.write("test.py", "print('hello')")
        assert result is True
        assert (tmp_path / "test.py").read_text() == "print('hello')"
    finally:
        os.chdir(original_dir)


def test_safe_file_writer_write_unsafe_path(tmp_path: Path) -> None:
    config = Config()
    writer = SafeFileWriter(config)
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = writer.write("../evil.py", "bad")
        assert result is False
    finally:
        os.chdir(original_dir)


def test_safe_file_writer_write_batch(tmp_path: Path) -> None:
    config = Config()
    writer = SafeFileWriter(config)
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        files = {"a.py": "content a", "b.py": "content b"}
        written = writer.write_batch(files)
        assert written == 2
        assert (tmp_path / "a.py").read_text() == "content a"
        assert (tmp_path / "b.py").read_text() == "content b"
    finally:
        os.chdir(original_dir)


def test_safe_file_writer_write_batch_truncate(tmp_path: Path) -> None:
    config = Config()
    config.max_files_per_batch = 2
    writer = SafeFileWriter(config)
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        files = {f"file{i}.py": f"content {i}" for i in range(5)}
        written = writer.write_batch(files)
        assert written == 2
    finally:
        os.chdir(original_dir)


def test_safe_file_writer_write_creates_dirs(tmp_path: Path) -> None:
    config = Config()
    writer = SafeFileWriter(config)
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = writer.write("deep/nested/dir/test.py", "content")
        assert result is True
        assert (tmp_path / "deep" / "nested" / "dir" / "test.py").read_text() == "content"
    finally:
        os.chdir(original_dir)
