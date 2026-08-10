"""Tests for read_file."""

from repopilot.tools.read_file import read_file
from repopilot.workspace import Workspace


def test_read_file_success(tmp_path):
    (tmp_path / "hello.txt").write_text("Hello RepoPilot!", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = read_file("hello.txt", workspace=workspace)

    assert result.success is True
    assert result.output == "Hello RepoPilot!"
    assert result.error is None


def test_read_file_missing(tmp_path):
    workspace = Workspace(tmp_path)

    result = read_file("missing.txt", workspace=workspace)

    assert result.success is False
    assert result.error == "File not found: missing.txt"


def test_read_file_rejects_path_traversal(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = read_file("../outside.txt", workspace=workspace)

    assert result.success is False
    assert "escapes the repository" in result.error


def test_read_file_rejects_absolute_path_outside_repo(tmp_path):
    outside = tmp_path.parent / "absolute_outside.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = read_file(str(outside.resolve()), workspace=workspace)

    assert result.success is False
    assert "escapes the repository" in result.error


def test_read_file_invalid_utf8(tmp_path):
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
    workspace = Workspace(tmp_path)

    result = read_file("bad.txt", workspace=workspace)

    assert result.success is False
    assert result.error == "Invalid UTF-8: bad.txt"


def test_read_file_directory(tmp_path):
    (tmp_path / "subdir").mkdir()
    workspace = Workspace(tmp_path)

    result = read_file("subdir", workspace=workspace)

    assert result.success is False
    assert result.error is not None
