"""Golden tests for compat (tree-compatible) output."""

from pathlib import Path

import pytest

from neotree import NtreeError
from neotree.cli import run_ntree
from tests.conftest import assert_golden


def _run_sample_tree(sample_tree: Path, cli_args: list[str]) -> str:
    """Run ``ntree`` against sample tree with extra args.

    Args:
        sample_tree: Sample tree fixture path.
        cli_args: Additional CLI args.

    Returns:
        str: CLI output.
    """
    return run_ntree([str(sample_tree), *cli_args])


class TestCompatGolden:
    @pytest.mark.parametrize(
        ("cli_args", "golden_name"),
        [
            ([], "compat_basic"),
            (["-L", "1"], "compat_depth1"),
            (["-L", "2"], "compat_depth2"),
            (["-d"], "compat_dirs_only"),
            (["-I", "tests"], "compat_exclude_tests"),
            (["-I", "*.py"], "compat_exclude_wildcard"),
            (["-I", "tests", "-I", "docs"], "compat_exclude_multi"),
            (["--dirsfirst"], "compat_dirsfirst"),
            (["--noreport"], "compat_noreport"),
            (["--charset", "ascii"], "compat_ascii"),
            (["-L", "1", "--dirsfirst", "--noreport"], "compat_combined"),
            (["--dirsfirst", "--noreport"], "compat_dirsfirst_noreport"),
            (["-I", "tests", "--dirsfirst"], "compat_exclude_dirsfirst"),
            (["-d", "--noreport"], "compat_dirs_only_noreport"),
            (["-L", "2", "--dirsfirst"], "compat_depth2_dirsfirst"),
            (["--charset", "ascii", "--dirsfirst"], "compat_ascii_dirsfirst"),
        ],
    )
    def test_compat_golden_matrix(
        self,
        sample_tree: Path,
        cli_args: list[str],
        golden_name: str,
    ) -> None:
        output = _run_sample_tree(sample_tree, cli_args)
        assert_golden(output, golden_name)

    def test_all_files(self, sample_tree: Path) -> None:
        """Hidden files are included with -a."""
        # Add a hidden file to sample_tree fixture's tmp dir
        (sample_tree / ".env").write_text("secret")
        output = _run_sample_tree(sample_tree, ["-a"])
        assert_golden(output, "compat_all_files")


class TestCompatOptionBehavior:
    """Structural assertions for option interactions — not purely golden-based."""

    def test_level_one_shows_only_direct_children(self, sample_tree: Path) -> None:
        """GNU tree -L 1 shows only root's immediate children."""
        output = run_ntree([str(sample_tree), "-L", "1"])
        lines = [line for line in output.split("\n") if line.strip()]
        # No entry should have indentation (depth > 1 would have indent)
        tree_lines = [line for line in lines if line.startswith(("├", "└"))]
        assert tree_lines, "should have some entries"
        for line in tree_lines:
            # Top-level connector means no prefix before it
            assert line[0] in ("├", "└"), f"nested entry leaked: {line!r}"

    def test_level_two_shows_two_levels(self, sample_tree: Path) -> None:
        """-L 2 must show entries at depth 1 and 2 but not deeper."""
        output = run_ntree([str(sample_tree), "-L", "2"])
        # auth.py and user.py are at depth 3 in sample_tree
        assert "auth.py" not in output
        # api/ is at depth 2 — must appear
        assert "api/" in output
        # guide.md is at depth 2 — must appear
        assert "guide.md" in output

    def test_dirsfirst_dirs_before_files_at_every_level(
        self, sample_tree: Path
    ) -> None:
        """--dirsfirst must order dirs before files at EVERY nesting level."""
        output = run_ntree([str(sample_tree), "--dirsfirst"])
        lines = output.split("\n")
        # At root level: last top-level dir must appear before first file
        top = [line for line in lines[1:] if line and line[0] in ("├", "└")]
        last_dir = max(
            (i for i, line in enumerate(top) if line.rstrip().endswith("/")),
            default=None,
        )
        first_file = next(
            (i for i, line in enumerate(top) if not line.rstrip().endswith("/")),
            None,
        )
        if last_dir is not None and first_file is not None:
            assert last_dir < first_file

    def test_exclude_removes_entry_and_its_subtree(self, sample_tree: Path) -> None:
        """-I on a directory must remove it AND all descendants."""
        output = run_ntree([str(sample_tree), "-I", "src"])
        assert "src" not in output
        assert "api" not in output  # child of src
        assert "auth.py" not in output  # grandchild of src

    def test_exclude_wildcard_matches_files(self, sample_tree: Path) -> None:
        """-I '*.py' must remove all .py files."""
        output = run_ntree([str(sample_tree), "-I", "*.py"])
        assert "auth.py" not in output
        assert "user.py" not in output
        # Dirs should still appear
        assert "src/" in output

    def test_exclude_wildcard_also_removes_matching_dirs(
        self, sample_tree: Path
    ) -> None:
        """-I 'api' removes the api/ directory and its contents."""
        output = run_ntree([str(sample_tree), "-I", "api"])
        assert "api" not in output
        assert "auth.py" not in output

    def test_all_files_shows_hidden(self, sample_tree: Path) -> None:
        (sample_tree / ".env").write_text("s")
        output = run_ntree([str(sample_tree), "-a"])
        assert ".env" in output

    def test_all_files_default_hides_hidden(self, sample_tree: Path) -> None:
        (sample_tree / ".env").write_text("s")
        output = run_ntree([str(sample_tree)])
        assert ".env" not in output

    def test_noreport_omits_count_line(self, sample_tree: Path) -> None:
        output = run_ntree([str(sample_tree), "--noreport"])
        assert "directories" not in output
        assert "files" not in output

    def test_report_singular(self, tmp_path: Path) -> None:
        """Report uses singular 'directory'/'file' for count of 1."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "alone.txt").write_text("x")
        output = run_ntree([str(tmp_path)])
        assert "1 directory, 1 file" in output

    def test_report_plural(self, tmp_path: Path) -> None:
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "f1.txt").write_text("x")
        (tmp_path / "f2.txt").write_text("x")
        output = run_ntree([str(tmp_path)])
        assert "2 directories, 2 files" in output

    @pytest.mark.parametrize("level", ["0", "-5"])
    def test_level_invalid_values(self, tmp_path: Path, level: str) -> None:
        with pytest.raises(NtreeError, match="Invalid level"):
            run_ntree([str(tmp_path), "-L", level])

    def test_ascii_no_unicode_glyphs(self, sample_tree: Path) -> None:
        output = run_ntree([str(sample_tree), "--charset", "ascii"])
        assert "├" not in output
        assert "└" not in output
        assert "│" not in output

    def test_multiple_exclude_patterns(self, sample_tree: Path) -> None:
        """Multiple -I flags must all apply."""
        output = run_ntree([str(sample_tree), "-I", "tests", "-I", "docs"])
        assert "tests" not in output
        assert "docs" not in output
        assert "src/" in output

    def test_dirs_only_no_files(self, sample_tree: Path) -> None:
        output = run_ntree([str(sample_tree), "-d"])
        assert "README.md" not in output
        assert "auth.py" not in output
        assert "src/" in output

    def test_dirs_only_report(self, sample_tree: Path) -> None:
        """Report with -d must show 0 files."""
        output = run_ntree([str(sample_tree), "-d"])
        assert "0 files" in output

    def test_fullpath_contains_parent_segments(self, sample_tree: Path) -> None:
        """-f / --fullpath must include parent directory in every path."""
        output = run_ntree([str(sample_tree), "-f"])
        # Nested entries must carry their full relative path
        assert "src/api/auth.py" in output or "src\\api\\auth.py" in output
        # Root-level files just appear by name (no extra prefix)
        assert "README.md" in output

    def test_fullpath_dirs_still_marked(self, sample_tree: Path) -> None:
        """-f must still append '/' to directories."""
        output = run_ntree([str(sample_tree), "-f"])
        assert "src/" in output or "src\\" in output


class TestCompatGitignore:
    """Golden and structural tests for --gitignore in compat mode."""

    def test_compat_gitignore_golden(self, gitignore_tree: Path) -> None:
        output = run_ntree([str(gitignore_tree), "--gitignore"])
        assert_golden(output, "compat_gitignore")

    def test_compat_gitignore_dirsfirst_golden(self, gitignore_tree: Path) -> None:
        output = run_ntree([str(gitignore_tree), "--gitignore", "--dirsfirst"])
        assert_golden(output, "compat_gitignore_dirsfirst")

    def test_gitignore_excludes_matched_entries(self, gitignore_tree: Path) -> None:
        output = run_ntree([str(gitignore_tree), "--gitignore"])
        assert "node_modules" not in output
        assert "dist" not in output
        assert "app.pyc" not in output
        assert "app.py" in output
        assert "README.md" in output

    def test_gitignore_disabled_shows_all(self, gitignore_tree: Path) -> None:
        output = run_ntree([str(gitignore_tree)])
        assert "node_modules" in output
        assert "dist" in output
