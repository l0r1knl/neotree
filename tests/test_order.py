"""Tests for --order option (name sort direction: asc / desc)."""

from pathlib import Path

import pytest

from neotree.cli import run_ntree
from neotree.formatter.compat import CompatOptions, format_compat
from neotree.formatter.csv_ import CsvOptions, format_csv
from neotree.formatter.short import ShortOptions, format_short
from neotree.scanner import Entry


def _file(name: str, parent: Path, depth: int = 0) -> Entry:
    """Return a file Entry under the given parent."""
    return Entry(
        path=parent / name,
        name=name,
        is_dir=False,
        depth=depth,
        parent_path=parent,
    )


def _dir(name: str, parent: Path, depth: int = 0) -> Entry:
    """Return a directory Entry under the given parent."""
    return Entry(
        path=parent / name,
        name=name,
        is_dir=True,
        depth=depth,
        parent_path=parent,
    )


ROOT = Path("/fake/root")


def _names_from_compat(result: str) -> list[str]:
    """Extract entry names from compat output lines."""
    return [
        line.split("\u2500\u2500 ")[1].rstrip("/")
        for line in result.splitlines()
        if "\u2500\u2500 " in line
    ]


# ---------------------------------------------------------------------------
# CompatOptions.order
# ---------------------------------------------------------------------------


class TestCompatOrder:
    def test_default_is_asc(self) -> None:
        entries = [_file("z.txt", ROOT), _file("a.txt", ROOT), _file("m.txt", ROOT)]
        result = format_compat(entries, CompatOptions())
        assert _names_from_compat(result) == ["a.txt", "m.txt", "z.txt"]

    def test_asc_explicit(self) -> None:
        entries = [_file("z.txt", ROOT), _file("a.txt", ROOT)]
        result = format_compat(entries, CompatOptions(order="asc"))
        assert _names_from_compat(result) == ["a.txt", "z.txt"]

    def test_desc(self) -> None:
        entries = [_file("a.txt", ROOT), _file("m.txt", ROOT), _file("z.txt", ROOT)]
        result = format_compat(entries, CompatOptions(order="desc"))
        assert _names_from_compat(result) == ["z.txt", "m.txt", "a.txt"]

    def test_desc_preserves_report(self) -> None:
        entries = [_file("b.txt", ROOT), _file("a.txt", ROOT)]
        result = format_compat(entries, CompatOptions(order="desc"))
        assert "0 directories, 2 files" in result

    def test_desc_with_dirsfirst(self) -> None:
        """dirs descending first, then files descending."""
        entries = [
            _dir("b_dir", ROOT),
            _dir("a_dir", ROOT),
            _file("z.txt", ROOT),
            _file("a.txt", ROOT),
        ]
        result = format_compat(entries, CompatOptions(dirs_first=True, order="desc"))
        assert _names_from_compat(result) == ["b_dir", "a_dir", "z.txt", "a.txt"]

    def test_asc_with_dirsfirst(self) -> None:
        """dirs ascending first, then files ascending (existing behaviour)."""
        entries = [
            _dir("b_dir", ROOT),
            _dir("a_dir", ROOT),
            _file("z.txt", ROOT),
            _file("a.txt", ROOT),
        ]
        result = format_compat(entries, CompatOptions(dirs_first=True, order="asc"))
        assert _names_from_compat(result) == ["a_dir", "b_dir", "a.txt", "z.txt"]


class TestShortOrder:
    def test_default_asc_preserved(self) -> None:
        """Files in asc scan order remain asc (no reorder for default)."""
        entries = [_file("a.txt", ROOT), _file("m.txt", ROOT), _file("z.txt", ROOT)]
        result = format_short(entries, ShortOptions(root_path=ROOT))
        assert "a.txt, m.txt, z.txt" in result

    def test_desc(self) -> None:
        entries = [_file("a.txt", ROOT), _file("m.txt", ROOT), _file("z.txt", ROOT)]
        result = format_short(entries, ShortOptions(root_path=ROOT, order="desc"))
        assert "z.txt, m.txt, a.txt" in result

    def test_desc_multiple_groups(self) -> None:
        """Each group is independently reversed."""
        sub = ROOT / "sub"
        entries = [
            _file("a.txt", ROOT),
            _file("z.txt", ROOT),
            _file("b.txt", sub, depth=1),
            _file("y.txt", sub, depth=1),
        ]
        result = format_short(entries, ShortOptions(root_path=ROOT, order="desc"))
        lines = result.splitlines()
        root_line = next(line for line in lines if line.startswith("."))
        sub_line = next(line for line in lines if "sub" in line)
        assert root_line.endswith("z.txt, a.txt")
        assert sub_line.endswith("y.txt, b.txt")


def _csv_filenames(result: str) -> list[str]:
    """Extract filename column values from CSV output (skips header)."""
    rows = result.splitlines()[1:]
    return [r.split(",")[1] for r in rows if r]


class TestCsvOrder:
    def test_default_asc_preserved(self) -> None:
        entries = [_file("a.txt", ROOT), _file("m.txt", ROOT), _file("z.txt", ROOT)]
        result = format_csv(entries, CsvOptions(root_path=ROOT))
        assert _csv_filenames(result) == ["a.txt", "m.txt", "z.txt"]

    def test_desc(self) -> None:
        entries = [_file("a.txt", ROOT), _file("m.txt", ROOT), _file("z.txt", ROOT)]
        result = format_csv(entries, CsvOptions(root_path=ROOT, order="desc"))
        assert _csv_filenames(result) == ["z.txt", "m.txt", "a.txt"]

    def test_desc_multiple_parents(self) -> None:
        """Desc sort applies within each parent group independently."""
        sub = ROOT / "sub"
        entries = [
            _file("a.txt", ROOT),
            _file("z.txt", ROOT),
            _file("b.txt", sub, depth=1),
            _file("y.txt", sub, depth=1),
        ]
        result = format_csv(entries, CsvOptions(root_path=ROOT, order="desc"))
        assert _csv_filenames(result) == ["z.txt", "a.txt", "y.txt", "b.txt"]

    def test_desc_files_only(self) -> None:
        """files_only + desc: directories skipped, remaining entries desc."""
        entries = [
            _file("a.txt", ROOT),
            _file("z.txt", ROOT),
            _dir("docs", ROOT),
        ]
        result = format_csv(
            entries, CsvOptions(root_path=ROOT, order="desc", files_only=True)
        )
        assert _csv_filenames(result) == ["z.txt", "a.txt"]


class TestCLIOrder:
    def test_order_desc_compat(self, tmp_path: Path) -> None:
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = run_ntree([str(tmp_path), "--order", "desc"])
        assert _names_from_compat(result) == ["c.txt", "b.txt", "a.txt"]

    def test_order_asc_equals_default(self, tmp_path: Path) -> None:
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "a.txt").write_text("a")
        default = run_ntree([str(tmp_path)])
        explicit = run_ntree([str(tmp_path), "--order", "asc"])
        assert default == explicit

    def test_order_desc_short(self, tmp_path: Path) -> None:
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "a.txt").write_text("a")
        result = run_ntree([str(tmp_path), "--short", "--order", "desc"])
        assert "c.txt, a.txt" in result

    def test_order_desc_csv(self, tmp_path: Path) -> None:
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "a.txt").write_text("a")
        result = run_ntree([str(tmp_path), "--csv", "--order", "desc"])
        assert _csv_filenames(result) == ["c.txt", "a.txt"]

    def test_order_invalid_value(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            run_ntree([str(tmp_path), "--order", "random"])

    def test_order_desc_with_dirsfirst(self, tmp_path: Path) -> None:
        (tmp_path / "z.txt").write_text("z")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "sub").mkdir()
        result = run_ntree([str(tmp_path), "--dirsfirst", "--order", "desc"])
        # Extract raw names (with trailing "/" for dirs) to distinguish dirs vs files
        raw_names = [
            line.split("── ")[1] for line in result.splitlines() if "── " in line
        ]
        assert raw_names == ["sub/", "z.txt", "a.txt"]
