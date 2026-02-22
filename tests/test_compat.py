"""Tests for neotree.formatter.compat — tree-compatible box-drawing output."""

from pathlib import Path

import pytest

from neotree.formatter.compat import CompatOptions, format_compat
from neotree.scanner import Entry, ScanOptions, scan


def _build_compat_tree(tmp_path: Path) -> Path:
    """Standard test tree for formatter tests."""
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "a1.txt").write_text("a1")
    (tmp_path / "alpha" / "a2.txt").write_text("a2")
    (tmp_path / "beta").mkdir()
    (tmp_path / "beta" / "b1.txt").write_text("b1")
    (tmp_path / "gamma.txt").write_text("g")
    return tmp_path


def _scan_compat_tree(
    tmp_path: Path,
    options: ScanOptions | None = None,
) -> tuple[Path, list[Entry]]:
    """Build and scan the standard formatter test tree.

    Args:
        tmp_path: Pytest temporary directory fixture.
        options: Optional scanner options.

    Returns:
        tuple[Path, list[Entry]]: Root path and scanned entries.
    """
    root = _build_compat_tree(tmp_path)
    entries = scan(root, options)
    return root, entries


class TestFormatCompatBasic:
    def test_basic_tree(self, tmp_path: Path) -> None:
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries)
        lines = output.split("\n")

        assert lines[0] == "."
        # Should contain directory and file markers
        assert "alpha/" in output
        assert "beta/" in output
        assert "gamma.txt" in output
        # Report line at the end
        assert "2 directories, 4 files" in output

    def test_empty_dir(self, tmp_path: Path) -> None:
        entries = scan(tmp_path)
        output = format_compat(entries)
        assert "0 directories, 0 files" in output

    def test_noreport(self, tmp_path: Path) -> None:
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries, CompatOptions(no_report=True))
        assert "directories" not in output
        assert "files" not in output

    @pytest.mark.parametrize("charset", ["ascii", "unicode"])
    def test_charset(self, tmp_path: Path, charset: str) -> None:
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries, CompatOptions(charset=charset))  # type: ignore[arg-type]
        if charset == "ascii":
            assert "|-- " in output or "\\-- " in output
            assert "├" not in output
        else:
            assert "├── " in output or "└── " in output

    def test_dirs_first(self, tmp_path: Path) -> None:
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries, CompatOptions(dirs_first=True))
        lines = output.split("\n")
        # At the top level, directories should come first
        top_level_items = [
            line
            for line in lines[1:]
            if line.startswith("├")
            or line.startswith("└")
            or line.startswith("|")
            or line.startswith("\\")
        ]
        first_file_idx = None
        last_dir_idx = None
        for i, item in enumerate(top_level_items):
            if item.rstrip().endswith("/"):
                last_dir_idx = i
            elif first_file_idx is None:
                first_file_idx = i
        if first_file_idx is not None and last_dir_idx is not None:
            assert last_dir_idx < first_file_idx

    def test_max_depth(self, tmp_path: Path) -> None:
        _, entries = _scan_compat_tree(tmp_path, ScanOptions(max_depth=0))
        output = format_compat(entries)
        assert "a1.txt" not in output
        assert "alpha/" in output

    def test_full_path(self, tmp_path: Path) -> None:
        root, entries = _scan_compat_tree(tmp_path)
        output = format_compat(
            entries,
            CompatOptions(full_path=True, root_path=root.resolve()),
        )
        assert "alpha/a1.txt" in output or "alpha\\a1.txt" in output


class TestFormatCompatStructure:
    def test_nested_indentation(self, tmp_path: Path) -> None:
        """Verify that nested entries have proper indentation."""
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries)
        lines = output.split("\n")

        # Lines with a1.txt/a2.txt should have extra indentation
        a1_lines = [line for line in lines if "a1.txt" in line]
        assert len(a1_lines) == 1
        a1_line = a1_lines[0]
        # Should have vertical line or space prefix before the connector
        assert (
            a1_line.startswith("│")
            or a1_line.startswith("|")
            or a1_line.startswith("    ")
        )

    def test_last_entry_uses_corner(self, tmp_path: Path) -> None:
        """The last entry at the root level should use └── not ├──."""
        _, entries = _scan_compat_tree(tmp_path)
        output = format_compat(entries)
        lines = output.split("\n")
        # Find last top-level entry
        top_level = [line for line in lines[1:] if line and line[0] in ("├", "└")]
        if top_level:
            assert top_level[-1].startswith("└")
