"""Tests for search_repo."""

from pathlib import Path

from repopilot.tools.search_repo import search_repo
from repopilot.workspace import Workspace


def test_search_repo_finds_matching_string(tmp_path):
    (tmp_path / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("hello", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "app.py", "line_number": 1, "line": "def hello():"}
    ]


def test_search_repo_is_case_insensitive(tmp_path):
    (tmp_path / "notes.txt").write_text("RepoPilot rocks\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("repopilot", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "notes.txt", "line_number": 1, "line": "RepoPilot rocks"}
    ]


def test_search_repo_returns_relative_paths(tmp_path):
    (tmp_path / "a.txt").write_text("findme\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("findme", workspace=workspace)

    assert result.success is True
    assert result.output[0]["path"] == "a.txt"
    assert not Path(result.output[0]["path"]).is_absolute()


def test_search_repo_uses_1_based_line_numbers(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\nmatch\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("match", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "a.txt", "line_number": 3, "line": "match"}
    ]


def test_search_repo_returns_matching_line_content(tmp_path):
    (tmp_path / "a.txt").write_text("keep this exact line\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("exact", workspace=workspace)

    assert result.success is True
    assert result.output[0]["line"] == "keep this exact line"


def test_search_repo_searches_nested_directories(tmp_path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("target = 1\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("target", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "src/pkg/mod.py", "line_number": 1, "line": "target = 1"}
    ]


def test_search_repo_ignores_excluded_directories(tmp_path):
    (tmp_path / "keep.py").write_text("needle\n", encoding="utf-8")
    for name in (".git", ".venv", "__pycache__", ".pytest_cache"):
        noise = tmp_path / name
        noise.mkdir()
        (noise / "ignored.txt").write_text("needle\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("needle", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "keep.py", "line_number": 1, "line": "needle"}
    ]


def test_search_repo_skips_invalid_utf8_files(tmp_path):
    (tmp_path / "good.txt").write_text("findme\n", encoding="utf-8")
    (tmp_path / "bad.bin").write_bytes(b"\xff\xfe findme")
    workspace = Workspace(tmp_path)

    result = search_repo("findme", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "good.txt", "line_number": 1, "line": "findme"}
    ]


def test_search_repo_returns_empty_list_when_no_matches(tmp_path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("zzz", workspace=workspace)

    assert result.success is True
    assert result.output == []


def test_search_repo_orders_matches_by_path_then_line_number(tmp_path):
    (tmp_path / "b.txt").write_text("x\nmatch\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("match first\nno\nmatch second\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = search_repo("match", workspace=workspace)

    assert result.success is True
    assert result.output == [
        {"path": "a.txt", "line_number": 1, "line": "match first"},
        {"path": "a.txt", "line_number": 3, "line": "match second"},
        {"path": "b.txt", "line_number": 2, "line": "match"},
    ]
