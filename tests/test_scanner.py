"""Tests for neotree.scanner."""

from pathlib import Path

import pytest

from neotree.scanner import ScanOptions, scan


def _build_scanner_tree(tmp_path: Path) -> Path:
    """Create a small test directory structure."""
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "a1.txt").write_text("a1")
    (tmp_path / "alpha" / "a2.txt").write_text("a2")
    (tmp_path / "beta").mkdir()
    (tmp_path / "beta" / "b1.txt").write_text("b1")
    (tmp_path / "gamma.txt").write_text("g")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "h.txt").write_text("h")
    return tmp_path


def _scan_entry_names(root: Path, options: ScanOptions | None = None) -> list[str]:
    """Scan root and return entry names.

    Args:
        root: Root path to scan.
        options: Optional scan options.

    Returns:
        list[str]: Entry names in scan order.
    """
    return [entry.name for entry in scan(root, options)]


class TestScanBasic:
    def test_scans_all_non_hidden(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        names = _scan_entry_names(root)
        assert "alpha" in names
        assert "beta" in names
        assert "gamma.txt" in names
        assert ".hidden" not in names  # hidden excluded by default

    def test_includes_hidden_with_all_files(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        names = _scan_entry_names(root, ScanOptions(all_files=True))
        assert ".hidden" in names

    def test_dirs_only(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        entries = scan(root, ScanOptions(dirs_only=True))
        assert all(e.is_dir for e in entries)
        names = [e.name for e in entries]
        assert "alpha" in names
        assert "gamma.txt" not in names

    @pytest.mark.parametrize(
        ("max_depth", "expected_present_names", "expected_absent_names"),
        [
            (0, ["alpha", "gamma.txt"], ["a1.txt"]),
            (1, ["alpha", "a1.txt"], []),
        ],
    )
    def test_max_depth(
        self,
        tmp_path: Path,
        max_depth: int,
        expected_present_names: list[str],
        expected_absent_names: list[str],
    ) -> None:
        root = _build_scanner_tree(tmp_path)
        names = _scan_entry_names(root, ScanOptions(max_depth=max_depth))
        for name in expected_present_names:
            assert name in names
        for name in expected_absent_names:
            assert name not in names

    def test_deterministic_order(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        entries1 = scan(root)
        entries2 = scan(root)
        assert [e.name for e in entries1] == [e.name for e in entries2]

    def test_entry_fields(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        entries = scan(root, ScanOptions(max_depth=0))
        alpha = next(e for e in entries if e.name == "alpha")
        assert alpha.is_dir is True
        assert alpha.depth == 0
        assert alpha.parent_path == root.resolve()

    def test_empty_dir(self, tmp_path: Path) -> None:
        entries = scan(tmp_path)
        assert entries == []

    def test_nonexistent_root(self, tmp_path: Path) -> None:
        entries = scan(tmp_path / "no_such_dir")
        assert entries == []


class TestScanWithFilter:
    def test_custom_filter_excludes(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)

        class ExcludeBeta:
            def should_exclude(self, name: str, is_dir: bool) -> bool:
                return name == "beta"

        entries = scan(root, entry_filter=ExcludeBeta())
        names = [e.name for e in entries]
        assert "beta" not in names
        assert "alpha" in names


def _build_gitignore_tree(tmp_path: Path) -> Path:
    """Create a tree with a .gitignore file for testing."""
    (tmp_path / ".gitignore").write_text("*.pyc\nnode_modules/\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "src" / "app.pyc").write_bytes(b"\x00")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("js")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


class TestScanWithGitignore:
    def test_gitignore_excludes_matching_files(self, tmp_path: Path) -> None:
        root = _build_gitignore_tree(tmp_path)
        entries = scan(root, ScanOptions(gitignore=True))
        names = [e.name for e in entries]
        assert "app.pyc" not in names
        assert "app.py" in names

    def test_gitignore_excludes_directory_and_contents(self, tmp_path: Path) -> None:
        root = _build_gitignore_tree(tmp_path)
        entries = scan(root, ScanOptions(gitignore=True))
        names = [e.name for e in entries]
        assert "node_modules" not in names
        assert "pkg" not in names
        assert "index.js" not in names

    def test_gitignore_disabled_by_default(self, tmp_path: Path) -> None:
        root = _build_gitignore_tree(tmp_path)
        entries = scan(root, ScanOptions())
        names = [e.name for e in entries]
        assert "app.pyc" in names
        assert "node_modules" in names

    def test_gitignore_no_gitignore_file_returns_all(self, tmp_path: Path) -> None:
        root = _build_scanner_tree(tmp_path)
        entries_without = scan(root)
        entries_with = scan(root, ScanOptions(gitignore=True))
        assert [e.name for e in entries_without] == [e.name for e in entries_with]

    def test_gitignore_with_exclude_filter_both_applied(self, tmp_path: Path) -> None:
        root = _build_gitignore_tree(tmp_path)

        class ExcludeReadme:
            def should_exclude(self, name: str, is_dir: bool) -> bool:
                return name == "README.md"

        entries = scan(root, ScanOptions(gitignore=True), entry_filter=ExcludeReadme())
        names = [e.name for e in entries]
        assert "README.md" not in names  # excluded by filter
        assert "app.pyc" not in names  # excluded by gitignore
        assert "node_modules" not in names  # excluded by gitignore
        assert "app.py" in names  # kept

    def test_gitignore_preserves_non_ignored_entries(self, tmp_path: Path) -> None:
        root = _build_gitignore_tree(tmp_path)
        entries = scan(root, ScanOptions(gitignore=True))
        names = [e.name for e in entries]
        assert "src" in names
        assert "app.py" in names
        assert "README.md" in names
