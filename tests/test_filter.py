"""Tests for neotree.filter."""

import pytest

from neotree.filter import PatternFilter


class TestPatternFilter:
    def test_no_patterns_excludes_nothing(self) -> None:
        f = PatternFilter()
        assert f.should_exclude("foo.py", False) is False
        assert f.should_exclude("node_modules", True) is False

    @pytest.mark.parametrize(
        ("patterns", "name", "is_dir", "expected"),
        [
            (["node_modules"], "node_modules", True, True),
            (["node_modules"], "src", True, False),
            (["*.pyc"], "foo.pyc", False, True),
            (["*.pyc"], "foo.py", False, False),
            (["test_*"], "test_foo.py", False, True),
            (["test_*"], "foo_test.py", False, False),
        ],
    )
    def test_pattern_matching(
        self,
        patterns: list[str],
        name: str,
        is_dir: bool,
        expected: bool,
    ) -> None:
        f = PatternFilter(patterns)
        assert f.should_exclude(name, is_dir) is expected

    def test_multiple_patterns(self) -> None:
        f = PatternFilter(["*.pyc", "node_modules", "__pycache__"])
        assert f.should_exclude("__pycache__", True) is True
        assert f.should_exclude("foo.pyc", False) is True
        assert f.should_exclude("src", True) is False
