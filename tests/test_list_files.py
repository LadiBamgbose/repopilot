"""Tests for list_files."""

from pathlib import Path

from repopilot.tools.list_files import list_files
from repopilot.workspace import Workspace


def test_list_files_recursively_lists_nested_files(tmp_path):
    (tmp_path / "README.md").write_text("root", encoding="utf-8")
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("code", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = list_files(workspace=workspace)

    assert result.success is True
    assert result.output == ["README.md", "src/pkg/mod.py"]


def test_list_files_returns_relative_paths(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = list_files(workspace=workspace)

    assert result.success is True
    assert result.output == ["a.txt"]
    assert not Path(result.output[0]).is_absolute()


def test_list_files_output_is_sorted(tmp_path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "m.txt").write_text("m", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = list_files(workspace=workspace)

    assert result.success is True
    assert result.output == ["a.txt", "m.txt", "z.txt"]


def test_list_files_ignores_excluded_directories(tmp_path):
    (tmp_path / "keep.py").write_text("keep", encoding="utf-8")
    for name in (".git", ".venv", "__pycache__", ".pytest_cache"):
        noise = tmp_path / name
        noise.mkdir()
        (noise / "ignored.txt").write_text("noise", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = list_files(workspace=workspace)

    assert result.success is True
    assert result.output == ["keep.py"]


def test_list_files_does_not_include_directories(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file.txt").write_text("nested", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = list_files(workspace=workspace)

    assert result.success is True
    assert result.output == ["subdir/file.txt"]
    assert "subdir" not in result.output
