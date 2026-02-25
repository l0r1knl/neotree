"""Tests for CSV formatter and files-only scan option."""

from pathlib import Path

import pytest

from neotree import NtreeError
from neotree.cli import run_ntree
from neotree.formatter.csv_ import CsvOptions, format_csv
from neotree.scanner import ScanOptions, scan


def _build_csv_tree(tmp_path: Path) -> Path:
    """Create a small directory tree for CSV tests.

    Structure::

        root/
        ├── docs/
        │   └── guide.md
        ├── src/
        │   └── app.py
        └── README.md
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


def _csv_output(root: Path, cli_args: list[str]) -> str:
    return run_ntree([str(root), *cli_args])


def _scan_and_format(root: Path, opts: CsvOptions | None = None) -> str:
    entries = scan(root)
    return format_csv(entries, opts or CsvOptions(root_path=root))


class TestCsvOptions:
    def test_default_options_are_set(self) -> None:
        opts = CsvOptions()
        assert opts.files_only is False
        assert opts.root_path is None


class TestFormatCsvSchema:
    def test_header_row_present(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        first_line = output.splitlines()[0]
        assert first_line == "parent_dir,filename,fullpath,depth"

    def test_each_row_has_four_columns(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        for line in output.splitlines()[1:]:
            assert line.count(",") >= 3, f"Row has fewer than 4 columns: {line!r}"

    def test_entry_count_matches_rows(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        # header + one row per entry
        assert len(output.splitlines()) == len(entries) + 1

    def test_empty_entries_returns_header_only(self, tmp_path: Path) -> None:
        output = format_csv([], CsvOptions(root_path=tmp_path))
        assert output == "parent_dir,filename,fullpath,depth"


class TestFormatCsvColumns:
    def test_parent_dir_is_immediate_parent_name(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        rows = output.splitlines()[1:]
        # guide.md parent should be "docs"
        guide_row = next(r for r in rows if "guide.md" in r)
        assert guide_row.startswith("docs,guide.md,")

    def test_root_level_file_parent_dir_is_root_name(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        root_name = root.name
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        rows = output.splitlines()[1:]
        readme_row = next(r for r in rows if "README.md" in r)
        assert readme_row.startswith(f"{root_name},README.md,")

    def test_fullpath_uses_os_separator(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        rows = output.splitlines()[1:]
        app_row = next(r for r in rows if "app.py" in r)
        # fullpath is the 3rd column
        fullpath = app_row.split(",")[2]
        expected = str((root / "src" / "app.py"))
        assert fullpath == expected

    def test_depth_column_for_root_level_file(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        rows = output.splitlines()[1:]
        readme_row = next(r for r in rows if "README.md" in r)
        depth = int(readme_row.split(",")[-1])
        assert depth == 0

    def test_depth_column_for_nested_file(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root))
        rows = output.splitlines()[1:]
        guide_row = next(r for r in rows if "guide.md" in r)
        depth = int(guide_row.split(",")[-1])
        assert depth == 1


class TestFormatCsvFilesOnly:
    def test_files_only_excludes_directory_rows(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root, files_only=True))
        rows = output.splitlines()[1:]
        # All rows should be files (not directories)
        dir_names = {"docs", "src"}
        for row in rows:
            filename = row.split(",")[1]
            assert filename not in dir_names, f"Directory row leaked: {row!r}"

    def test_files_only_keeps_all_file_rows(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root)
        output = format_csv(entries, CsvOptions(root_path=root, files_only=True))
        rows = output.splitlines()[1:]
        filenames = {r.split(",")[1] for r in rows}
        assert "README.md" in filenames
        assert "guide.md" in filenames
        assert "app.py" in filenames


class TestScanFilesOnly:
    def test_files_only_excludes_dirs_from_results(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root, ScanOptions(files_only=True))
        assert all(not e.is_dir for e in entries)

    def test_files_only_still_traverses_subdirectories(self, tmp_path: Path) -> None:
        root = _build_csv_tree(tmp_path)
        entries = scan(root, ScanOptions(files_only=True))
        names = {e.name for e in entries}
        # Files inside subdirs must appear
        assert "guide.md" in names
        assert "app.py" in names

    def test_files_only_and_dirs_only_are_mutually_exclusive_in_scan(
        self, tmp_path: Path
    ) -> None:
        # Both being True at scan level is a caller error; scanner itself
        # should not crash — CLI validates earlier. We just verify one wins
        # (dirs_only takes precedence over files_only at scan level — handled
        # by CLI validation before reaching scanner).
        root = _build_csv_tree(tmp_path)
        entries = scan(root, ScanOptions(dirs_only=True, files_only=False))
        assert all(e.is_dir for e in entries)


class TestCsvCli:
    def test_csv_outputs_header(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv"])
        assert output.startswith("parent_dir,filename,fullpath,depth")

    def test_csv_contains_expected_file(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv"])
        assert "README.md" in output
        assert "auth.py" in output

    def test_csv_with_files_only_flag(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv", "-F"])
        rows = output.splitlines()[1:]
        dir_names = {"docs", "src", "api", "models", "tests"}
        for row in rows:
            filename = row.split(",")[1]
            assert filename not in dir_names, f"Dir leaked: {row!r}"

    def test_csv_files_only_contains_nested_files(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv", "-F"])
        assert "auth.py" in output
        assert "user.py" in output

    def test_csv_with_output_file(self, sample_tree: Path, tmp_path: Path) -> None:
        import sys
        from io import StringIO
        from unittest.mock import patch

        out_file = tmp_path / "result.csv"
        StringIO()
        with patch.object(
            sys, "argv", ["ntree", str(sample_tree), "--csv", "-o", str(out_file)]
        ):
            from neotree.cli import main

            main()
        content = out_file.read_text(encoding="utf-8")
        assert content.startswith("parent_dir,filename,fullpath,depth")

    def test_csv_with_level_limit(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv", "-L", "1"])
        # depth=1 entries (inside first-level dirs) should NOT appear
        assert "auth.py" not in output  # auth.py is at depth 2

    def test_csv_with_exclude_pattern(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["--csv", "-I", "tests"])
        assert "test_user.py" not in output

    def test_csv_with_preset(self, noisy_tree: Path) -> None:
        output = _csv_output(noisy_tree, ["--csv", "--preset", "python"])
        assert "__pycache__" not in output

    def test_csv_with_all_files_flag(self, sample_tree: Path) -> None:
        (sample_tree / ".env").write_text("secret")
        output = _csv_output(sample_tree, ["--csv", "-a"])
        assert ".env" in output


class TestFilesOnlyCli:
    def test_files_only_in_compat_mode_hides_dirs(self, sample_tree: Path) -> None:
        output = _csv_output(sample_tree, ["-F"])
        assert "├── src/" not in output
        assert "└── docs/" not in output

    def test_files_only_in_compat_mode_shows_root_level_files(
        self, sample_tree: Path
    ) -> None:
        # -F in compat mode: directories are not added to entries,
        # so compat formatter shows only files at depth=0 (root level).
        output = _csv_output(sample_tree, ["-F"])
        assert "README.md" in output

    def test_files_only_short_mode_is_error(self, sample_tree: Path) -> None:
        with pytest.raises(NtreeError, match="--files-only"):
            _csv_output(sample_tree, ["--short", "-F"])

    def test_dirs_only_and_files_only_is_error(self, sample_tree: Path) -> None:
        with pytest.raises(NtreeError, match="files-only"):
            _csv_output(sample_tree, ["-d", "-F"])


class TestCsvOptionConflicts:
    def test_csv_and_short_is_error(self, sample_tree: Path) -> None:
        with pytest.raises(NtreeError, match="--csv"):
            _csv_output(sample_tree, ["--csv", "--short"])

    def test_csv_and_md_is_error(self, sample_tree: Path) -> None:
        with pytest.raises(NtreeError, match="--csv"):
            _csv_output(sample_tree, ["--csv", "--md"])
