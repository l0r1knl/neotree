"""Tests for neotree.cli — CLI entry point.

Tests here cover:
  - Error paths (nonexistent dir, invalid -L, invalid preset, incompatible options)
  - I/O paths (-o output file)
  - Smoke tests that touch the full stack with a realistic tree (node_modules etc.)

Detailed option behaviour and option-combination correctness is delegated to
test_golden_compat.py::TestCompatOptionBehavior and
test_golden_short.py::TestShortOptionBehavior which use the canonical sample_tree
fixture and carry both golden snapshots and structural assertions.
"""

from pathlib import Path

import pytest

from neotree import NtreeError
from neotree.cli import run_ntree


def _build_tree(tmp_path: Path) -> Path:
    """Realistic test tree including 'noise' directories like node_modules."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("main")
    (tmp_path / "src" / "utils.py").write_text("utils")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("test")
    (tmp_path / "README.md").write_text("readme")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg").mkdir()
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("js")
    return tmp_path


class TestRunNtree:
    # ------------------------------------------------------------------
    # Smoke / full-stack checks
    # ------------------------------------------------------------------
    def test_default_output(self, tmp_path: Path) -> None:
        root = _build_tree(tmp_path)
        output = run_ntree([str(root)])
        assert "." == output.split("\n")[0]
        assert "src/" in output
        assert "README.md" in output

    def test_max_depth(self, tmp_path: Path) -> None:
        root = _build_tree(tmp_path)
        output = run_ntree([str(root), "-L", "1"])
        # GNU tree -L 1: root's immediate children only
        assert "src/" in output
        assert "main.py" not in output

    def test_exclude_node_modules(self, tmp_path: Path) -> None:
        """Realistic use: -I node_modules on a JS project tree."""
        root = _build_tree(tmp_path)
        output = run_ntree([str(root), "-I", "node_modules"])
        assert "node_modules" not in output
        assert "src/" in output

    def test_multiple_exclude(self, tmp_path: Path) -> None:
        root = _build_tree(tmp_path)
        output = run_ntree([str(root), "-I", "node_modules", "-I", "tests"])
        assert "node_modules" not in output
        assert "tests" not in output
        assert "src/" in output

    def test_output_file(self, tmp_path: Path) -> None:
        """-o returns the string; main() handles actual file write."""
        root = _build_tree(tmp_path)
        out_file = tmp_path / "output.txt"
        output = run_ntree([str(root), "-o", str(out_file)])
        assert "src/" in output

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------
    def test_nonexistent_directory(self) -> None:
        with pytest.raises(NtreeError, match="not a directory"):
            run_ntree(["/nonexistent/path/xyz"])

    @pytest.mark.parametrize("level", ["0", "-1"])
    def test_max_depth_invalid_values(self, tmp_path: Path, level: str) -> None:
        with pytest.raises(NtreeError, match="Invalid level"):
            run_ntree([str(tmp_path), "-L", level])

    def test_invalid_preset_raises_ntree_error(self, tmp_path: Path) -> None:
        """Invalid --preset must raise NtreeError, not ValueError."""
        root = _build_tree(tmp_path)
        with pytest.raises(NtreeError, match="Unknown preset"):
            run_ntree([str(root), "--preset", "java"])

    @pytest.mark.parametrize("preset", ["python", "node", "rust"])
    def test_valid_preset_works(self, tmp_path: Path, preset: str) -> None:
        """Known presets must not raise errors.

        Args:
            tmp_path: Pytest temporary directory fixture.
            preset: Preset name to test.
        """
        root = _build_tree(tmp_path)
        output = run_ntree([str(root), "--preset", preset])
        assert "Traceback" not in output
        assert "." == output.split("\n")[0]

    # ------------------------------------------------------------------
    # Incompatible option combinations
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("argv", "match"),
        [
            (["--short", "-d"], "incompatible"),
            (["--budget", "100"], "--budget"),
            (["--count"], "--count"),
        ],
    )
    def test_incompatible_option_combinations(
        self,
        tmp_path: Path,
        argv: list[str],
        match: str,
    ) -> None:
        with pytest.raises(NtreeError, match=match):
            run_ntree([str(tmp_path), *argv])

    @pytest.mark.parametrize("budget", ["0", "-1", "-100"])
    def test_budget_invalid_values(self, tmp_path: Path, budget: str) -> None:
        """--budget with non-positive values must raise NtreeError."""
        with pytest.raises(NtreeError, match="--budget must be a positive integer"):
            run_ntree([str(tmp_path), "--short", "--budget", budget])


def _build_gitignore_cli_tree(tmp_path: Path) -> Path:
    """Create a tree with .gitignore for CLI-level tests."""
    (tmp_path / ".gitignore").write_text("*.pyc\nnode_modules/\ndist/\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "src" / "app.pyc").write_bytes(b"\x00")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("js")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("bundle")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


class TestGitignoreCli:
    def test_gitignore_excludes_matching_entries(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore", "-a"])
        assert "node_modules" not in output
        assert "app.pyc" not in output
        assert "dist" not in output
        assert "app.py" in output
        assert "README.md" in output

    def test_gitignore_with_short_mode(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore", "--short", "-a"])
        assert "node_modules" not in output
        assert "app.pyc" not in output
        assert "app.py" in output

    def test_gitignore_with_csv_mode(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore", "--csv", "-a"])
        assert "node_modules" not in output
        assert "app.pyc" not in output
        assert "app.py" in output

    def test_gitignore_with_exclude_pattern(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore", "-I", "README.md", "-a"])
        assert "README.md" not in output
        assert "node_modules" not in output
        assert "app.py" in output

    def test_gitignore_with_preset(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore", "--preset", "python", "-a"])
        assert "node_modules" not in output
        assert "app.py" in output

    def test_gitignore_disabled_by_default(self, tmp_path: Path) -> None:
        root = _build_gitignore_cli_tree(tmp_path)
        output = run_ntree([str(root), "-a"])
        assert "node_modules" in output
        assert "app.pyc" in output

    def test_gitignore_no_gitignore_file(self, tmp_path: Path) -> None:
        root = _build_tree(tmp_path)
        output = run_ntree([str(root), "--gitignore"])
        assert "src/" in output
        assert "README.md" in output
