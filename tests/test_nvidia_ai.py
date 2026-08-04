import os
import tempfile

from nvidia_ai import is_safe_path, parse_json_from_llm, write_fix_files


def test_parse_json_from_llm_plain() -> None:
    text = '{"labels": ["bug"], "priority": "high"}'
    result = parse_json_from_llm(text)
    assert result is not None
    assert result["labels"] == ["bug"]
    assert result["priority"] == "high"


def test_parse_json_from_llm_with_fences() -> None:
    text = '```json\n{"labels": ["bug"], "priority": "high"}\n```'
    result = parse_json_from_llm(text)
    assert result is not None
    assert result["labels"] == ["bug"]


def test_parse_json_from_llm_with_fences_no_lang() -> None:
    text = '```\n{"labels": ["bug"]}\n```'
    result = parse_json_from_llm(text)
    assert result is not None
    assert result["labels"] == ["bug"]


def test_parse_json_from_llm_invalid() -> None:
    result = parse_json_from_llm("not json at all")
    assert result is None


def test_parse_json_from_llm_empty() -> None:
    result = parse_json_from_llm("")
    assert result is None


def test_is_safe_path_normal() -> None:
    assert is_safe_path("app.py") is True
    assert is_safe_path("src/main.py") is True
    assert is_safe_path("tests/test_app.py") is True


def test_is_safe_path_blocked() -> None:
    assert is_safe_path(".github/workflows/ci.yml") is False
    assert is_safe_path(".env") is False
    assert is_safe_path("secret.key") is False
    assert is_safe_path("credentials.json") is False


def test_is_safe_path_traversal() -> None:
    assert is_safe_path("../../etc/passwd") is False
    assert is_safe_path("../../.env") is False
    assert is_safe_path("subdir/../../../etc/hosts") is False


def test_is_safe_path_node_modules() -> None:
    assert is_safe_path("node_modules/package/index.js") is False


def test_write_fix_files_safe_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            output = "===FILE:test_write.txt===\nhello world\n===END==="
            write_fix_files(output, backup=False)
            with open("test_write.txt") as f:
                assert f.read() == "hello world"
        finally:
            os.chdir(original_cwd)


def test_write_fix_files_skips_protected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            output = "===FILE:.github/config.yml===\nbad\n===END==="
            write_fix_files(output, backup=False)
            assert not os.path.exists(".github/config.yml")
        finally:
            os.chdir(original_cwd)


def test_write_fix_files_multiple_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            output = "===FILE:a.py===\ncontent a\n===END===\n===FILE:b.py===\ncontent b\n===END==="
            write_fix_files(output, backup=False)
            with open("a.py") as f:
                assert f.read() == "content a"
            with open("b.py") as f:
                assert f.read() == "content b"
        finally:
            os.chdir(original_cwd)
