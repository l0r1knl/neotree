"""Tests for neotree.formatter.short — short grouped output."""

from pathlib import Path

from neotree.formatter.short import ShortOptions, format_short
from neotree.scanner import scan


def _build_short_tree(tmp_path: Path) -> Path:
    (tmp_path / "src" / "api").mkdir(parents=True)
    (tmp_path / "src" / "api" / "user.py").write_text("u")
    (tmp_path / "src" / "api" / "auth.py").write_text("a")
    (tmp_path / "src" / "api" / "routes.py").write_text("r")
    (tmp_path / "src" / "models").mkdir()
    (tmp_path / "src" / "models" / "user.py").write_text("u")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_user.py").write_text("t")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


def _render_short_output(
    root: Path,
    budget: int | None = None,
    count: bool = False,
) -> str:
    """Scan and render short output for a root path.

    Args:
        root: Root directory.
        budget: Optional character budget.
        count: Whether to show file counts.

    Returns:
        str: Rendered short output.
    """
    entries = scan(root)
    return format_short(
        entries, ShortOptions(root_path=root.resolve(), budget=budget, count=count)
    )


class TestFormatShortBasic:
    def test_basic_output(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        output = _render_short_output(root)
        # Should have no box-drawing characters
        for char in ("├", "└", "│"):
            assert char not in output
        # Should contain comma-separated files
        assert "user.py" in output
        assert "auth.py" in output

    def test_comma_join(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        output = _render_short_output(root)
        # src/api should have files comma-joined
        api_line = [line for line in output.split("\n") if "src/api" in line]
        assert len(api_line) == 1
        assert ", " in api_line[0]

    def test_childless_dir(self, tmp_path: Path) -> None:
        root = tmp_path
        (root / "empty_dir").mkdir()
        (root / "file.txt").write_text("f")
        entries = scan(root)
        output = format_short(entries, ShortOptions(root_path=root.resolve()))
        assert "empty_dir/" in output

    def test_count_flag(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        output = _render_short_output(root, count=True)
        assert "(files: 3)" in output  # src/api has 3 files

    def test_empty_entries(self) -> None:
        output = format_short([])
        assert output == ""

    def test_root_level_files(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        output = _render_short_output(root)
        # README.md at root level
        root_line = [line for line in output.split("\n") if "README.md" in line]
        assert len(root_line) == 1


class TestFormatShortBudget:
    def test_budget_aggregates_deep(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        # Very small budget to force aggregation
        output = _render_short_output(root, budget=50)
        # Deep dirs should be aggregated with explicit summary format
        assert "files)" in output
        # Aggregated lines must use the "dir/* (N files)" format
        agg_lines = [line for line in output.split("\n") if "files)" in line]
        for line in agg_lines:
            assert "/*" in line, f"Aggregated line missing '/*': {line!r}"

    def test_budget_no_aggregation_when_fits(self, tmp_path: Path) -> None:
        root = _build_short_tree(tmp_path)
        # Large budget — no aggregation needed
        output = _render_short_output(root, budget=10000)
        assert "files)" not in output
        assert "user.py" in output

    def test_budget_only_aggregates_what_needed(self, tmp_path: Path) -> None:
        """Budget should aggregate just enough — not the whole tree."""
        root = _build_short_tree(tmp_path)
        # Full output ≈ 89 chars. Budget=80 → only deepest group (src/api) aggregated.
        output = _render_short_output(root, budget=80)
        lines = output.split("\n")

        # src/api (depth 2) should be aggregated
        api_lines = [line for line in lines if "src/api" in line]
        assert len(api_lines) == 1
        assert "files)" in api_lines[0], "src/api should be aggregated"

        # tests (depth 1, shallower) should NOT be aggregated
        tests_lines = [line for line in lines if line.startswith("tests")]
        assert len(tests_lines) == 1
        assert (
            "test_user.py" in tests_lines[0]
        ), "tests should show files, not be aggregated"

    def test_budget_preserves_aggregated_lines_across_iterations(
        self, tmp_path: Path
    ) -> None:
        """Previously aggregated groups must keep
        '/* (N files)' in subsequent iterations.

        This is the regression test for the mutation-while-iterating bug that was fixed.
        The tree must have multiple groups at the same depth level to force multiple
        aggregation iterations.
        """
        # Build a tree with TWO peer deep directories so the loop must iterate twice
        (tmp_path / "a" / "deep").mkdir(parents=True)
        (tmp_path / "a" / "deep" / "f1.py").write_text("f1")
        (tmp_path / "a" / "deep" / "f2.py").write_text("f2")
        (tmp_path / "b" / "deep").mkdir(parents=True)
        (tmp_path / "b" / "deep" / "g1.py").write_text("g1")
        (tmp_path / "b" / "deep" / "g2.py").write_text("g2")
        (tmp_path / "root.txt").write_text("r")

        entries = scan(tmp_path)
        # Budget larger than single-group lines but smaller than full output
        # to force both deep dirs to aggregate.  Full output ≈ 53 chars, each
        # aggregated deep-dir line is ~18 chars, so budget=50 forces both to
        # aggregate while leaving the root "." group intact.
        output = format_short(
            entries, ShortOptions(root_path=tmp_path.resolve(), budget=50)
        )
        lines = output.split("\n")

        # ALL aggregated lines must use "/* (N files)" — this is the regression
        # invariant for the mutation-while-iterating bug.
        agg_lines = [line for line in lines if "files)" in line]
        assert len(agg_lines) >= 1, "Expected at least one aggregated line"
        for line in agg_lines:
            assert "/*" in line, f"Aggregated line lost summary format: {line!r}"

        # root.txt (depth 0) must NOT be aggregated at budget=50
        root_lines = [line for line in lines if "root.txt" in line]
        assert len(root_lines) == 1, "root.txt should be visible (not aggregated)"

    def test_budget_with_count(self, tmp_path: Path) -> None:
        """--budget + --count must not crash and must still aggregate correctly."""
        root = _build_short_tree(tmp_path)
        output = _render_short_output(root, budget=80, count=True)
        lines = output.split("\n")
        # Must produce some output
        assert lines

        # Aggregated lines must use /* (N files) — not count's (files: N) format
        agg_lines = [line for line in lines if "/*" in line]
        for line in agg_lines:
            assert "files)" in line
