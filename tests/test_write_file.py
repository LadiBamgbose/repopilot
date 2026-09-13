"""Tests for write_file."""

from pathlib import Path

from repopilot.tools.write_file import write_file
from repopilot.workspace import Workspace


def test_write_file_overwrites_existing_file(tmp_path):
    target = tmp_path / "example.py"
    target.write_text("print('old')\n", encoding="utf-8")
    workspace = Workspace(tmp_path)
    contents = "print('updated')\n"

    result = write_file("example.py", contents, workspace=workspace)

    assert result.success is True
    assert result.error is None
    assert result.output == {
        "path": "example.py",
        "bytes_written": len(contents.encode("utf-8")),
    }
    assert target.read_text(encoding="utf-8") == contents


def test_write_file_changes_contents_on_disk(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("before", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = write_file("notes.txt", "after", workspace=workspace)

    assert result.success is True
    assert target.read_text(encoding="utf-8") == "after"
    assert target.read_text(encoding="utf-8") != "before"


def test_write_file_returns_relative_path(tmp_path):
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    (nested / "mod.py").write_text("old", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = write_file("src/pkg/mod.py", "new", workspace=workspace)

    assert result.success is True
    assert result.output["path"] == "src/pkg/mod.py"
    assert not Path(result.output["path"]).is_absolute()


def test_write_file_returns_bytes_written(tmp_path):
    (tmp_path / "data.txt").write_text("x", encoding="utf-8")
    workspace = Workspace(tmp_path)
    contents = "café\n"

    result = write_file("data.txt", contents, workspace=workspace)

    assert result.success is True
    assert result.output["bytes_written"] == len(contents.encode("utf-8"))
    assert result.output["bytes_written"] == (tmp_path / "data.txt").stat().st_size


def test_write_file_rejects_path_traversal(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = write_file("../outside.txt", "overwrite", workspace=workspace)

    assert result.success is False
    assert "escapes the repository" in result.error
    assert outside.read_text(encoding="utf-8") == "secret"


def test_write_file_rejects_absolute_path_outside_repo(tmp_path):
    outside = tmp_path.parent / "absolute_outside.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = write_file(str(outside.resolve()), "overwrite", workspace=workspace)

    assert result.success is False
    assert "escapes the repository" in result.error
    assert outside.read_text(encoding="utf-8") == "secret"


def test_write_file_missing(tmp_path):
    workspace = Workspace(tmp_path)

    result = write_file("missing.txt", "new", workspace=workspace)

    assert result.success is False
    assert result.error == "File not found: missing.txt"
    assert not (tmp_path / "missing.txt").exists()


def test_write_file_directory(tmp_path):
    (tmp_path / "subdir").mkdir()
    workspace = Workspace(tmp_path)

    result = write_file("subdir", "nope", workspace=workspace)

    assert result.success is False
    assert result.error == "Is a directory: subdir"
    assert (tmp_path / "subdir").is_dir()


def test_write_file_does_not_create_missing_parent_directories(tmp_path):
    workspace = Workspace(tmp_path)

    result = write_file("missing/dir/file.txt", "new", workspace=workspace)

    assert result.success is False
    assert result.error == "File not found: missing/dir/file.txt"
    assert not (tmp_path / "missing").exists()
