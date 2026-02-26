"""Tests for gitignore module — .gitignore loading and matching."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from neotree.gitignore import load_gitignore_spec


class TestLoadGitignoreSpec:
    """Test load_gitignore_spec returns correct PathSpec or None."""

    def test_no_gitignore_returns_none(self, tmp_path: Path) -> None:
        assert load_gitignore_spec(tmp_path) is None

    @pytest.mark.parametrize(
        "content",
        [
            "*.pyc\n__pycache__/\n",
            "",
            "# comment line\n",
        ],
    )
    def test_gitignore_file_returns_spec(self, tmp_path: Path, content: str) -> None:
        (tmp_path / ".gitignore").write_text(content)
        assert load_gitignore_spec(tmp_path) is not None


class TestGitignoreMatching:
    """Test that loaded spec correctly matches files."""

    @pytest.mark.parametrize(
        ("gitignore_content", "path", "expected"),
        [
            # wildcard patterns
            ("*.pyc\n", "foo.pyc", True),
            ("*.pyc\n", "foo.py", False),
            # directory patterns
            ("__pycache__/\n", "__pycache__/", True),
            ("__pycache__/\n", "src/__pycache__/", True),
            # nested path matching
            ("node_modules/\n*.pyc\n", "node_modules/", True),
            ("node_modules/\n*.pyc\n", "deep/node_modules/", True),
            ("node_modules/\n*.pyc\n", "src/app.pyc", True),
            ("node_modules/\n*.pyc\n", "src/app.py", False),
            # multiple patterns
            ("*.log\ndist/\n.env\n", "error.log", True),
            ("*.log\ndist/\n.env\n", "dist/", True),
            ("*.log\ndist/\n.env\n", ".env", True),
            ("*.log\ndist/\n.env\n", "src/main.py", False),
            # empty gitignore matches nothing
            ("", "anything.py", False),
            # comment lines are ignored
            ("# ignore pyc\n*.pyc\n", "foo.pyc", True),
            ("# ignore pyc\n*.pyc\n", "# ignore pyc", False),
        ],
    )
    def test_pattern_matching(
        self, tmp_path: Path, gitignore_content: str, path: str, expected: bool
    ) -> None:
        (tmp_path / ".gitignore").write_text(gitignore_content)
        spec = load_gitignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file(path) is expected


class TestGitignoreErrorHandling:
    """Test graceful handling of filesystem errors."""

    @pytest.mark.skipif(os.name == "nt", reason="chmod not reliable on Windows")
    def test_unreadable_gitignore_returns_none(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")
        gitignore.chmod(0o000)
        try:
            assert load_gitignore_spec(tmp_path) is None
        finally:
            gitignore.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_nonexistent_root_returns_none(self, tmp_path: Path) -> None:
        assert load_gitignore_spec(tmp_path / "nonexistent") is None
