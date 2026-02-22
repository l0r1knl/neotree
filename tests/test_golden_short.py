"""Golden tests for short grouped output."""

from pathlib import Path

import pytest

from neotree import NtreeError
from neotree.cli import run_ntree
from tests.conftest import assert_golden


def _run_cli_for_root(root: Path, cli_args: list[str]) -> str:
    """Run ``ntree`` with root and additional arguments.

    Args:
        root: Target root path.
        cli_args: Additional CLI args.

    Returns:
        str: CLI output.
    """
    return run_ntree([str(root), *cli_args])


def _assert_md_wrapped(output: str, mode: str) -> None:
    """Assert markdown wrapper basics.

    Args:
        output: CLI output in markdown mode.
        mode: Expected mode metadata value.
    """
    assert output.startswith("## Project structure")
    assert f"- mode: {mode}" in output
    assert "```text" in output
    assert output.endswith("```")


class TestShortGolden:
    @pytest.mark.parametrize(
        ("root_fixture_name", "cli_args", "golden_name"),
        [
            ("sample_tree", ["--short"], "short_basic"),
            (
                "noisy_tree",
                ["--short", "--preset", "node", "-a"],
                "short_preset_node",
            ),
            ("sample_tree", ["--short", "--budget", "50"], "short_budget_over"),
            ("sample_tree", ["--short", "--count"], "short_count"),
            ("sample_tree", ["--short", "-L", "1"], "short_depth1"),
            ("sample_tree", ["--short", "-I", "tests"], "short_exclude_tests"),
            (
                "noisy_tree",
                ["--short", "--preset", "python"],
                "short_preset_python",
            ),
            (
                "sample_tree",
                ["--short", "--budget", "100", "--count"],
                "short_budget_count",
            ),
            ("sample_tree", ["--short", "-I", "*.py"], "short_exclude_wildcard"),
            (
                "sample_tree",
                ["--short", "-I", "tests", "-I", "docs"],
                "short_exclude_multi",
            ),
            ("sample_tree", ["--short", "-L", "2"], "short_depth2"),
        ],
    )
    def test_short_golden_matrix(
        self,
        request: pytest.FixtureRequest,
        root_fixture_name: str,
        cli_args: list[str],
        golden_name: str,
    ) -> None:
        root = request.getfixturevalue(root_fixture_name)
        output = _run_cli_for_root(root, cli_args)
        assert_golden(output, golden_name)

    def test_short_all_files(self, sample_tree: Path) -> None:
        """--short + -a shows hidden files."""
        (sample_tree / ".env").write_text("secret")
        output = _run_cli_for_root(sample_tree, ["--short", "-a"])
        assert_golden(output, "short_all_files")


class TestShortOptionBehavior:
    """Structural assertions for compact mode option interactions."""

    def test_short_depth1_shows_only_root_children(self, sample_tree: Path) -> None:
        """--short -L 1 shows only root-level entries."""
        output = _run_cli_for_root(sample_tree, ["--short", "-L", "1"])
        # No nested paths (no slashes in line keys except childless dirs)
        lines = output.split("\n")
        for line in lines:
            key = line.split(":")[0] if ":" in line else line
            # A nested path would look like "src/api: ..." — should not appear
            parts = key.strip("/").split("/")
            assert len(parts) <= 1, f"Nested path appeared under -L 1: {line!r}"

    def test_short_no_box_drawing(self, sample_tree: Path) -> None:
        output = _run_cli_for_root(sample_tree, ["--short"])
        for char in ("├", "└", "│", "|--", "\\--"):
            assert char not in output

    def test_short_exclude_removes_subtree(self, sample_tree: Path) -> None:
        output = _run_cli_for_root(sample_tree, ["--short", "-I", "src"])
        assert "src" not in output
        assert "auth.py" not in output

    def test_short_wildcard_exclude(self, sample_tree: Path) -> None:
        output = _run_cli_for_root(sample_tree, ["--short", "-I", "*.py"])
        assert "auth.py" not in output
        assert "user.py" not in output

    def test_short_count_shows_file_count_per_group(self, sample_tree: Path) -> None:
        output = _run_cli_for_root(sample_tree, ["--short", "--count"])
        # src/api has 2 files (auth.py, user.py)
        assert "(files: 2)" in output

    def test_short_preset_python_hides_pycache(self, noisy_tree: Path) -> None:
        output = _run_cli_for_root(noisy_tree, ["--short", "--preset", "python"])
        assert "__pycache__" not in output

    def test_short_all_shows_hidden(self, sample_tree: Path) -> None:
        (sample_tree / ".env").write_text("s")
        output = _run_cli_for_root(sample_tree, ["--short", "-a"])
        assert ".env" in output

    def test_budget_with_count_no_crash(self, sample_tree: Path) -> None:
        """--budget + --count must not crash."""
        output = _run_cli_for_root(
            sample_tree, ["--short", "--budget", "80", "--count"]
        )
        assert output  # non-empty

    def test_short_multiple_exclude(self, sample_tree: Path) -> None:
        output = _run_cli_for_root(
            sample_tree, ["--short", "-I", "tests", "-I", "docs"]
        )
        assert "tests" not in output
        assert "docs" not in output
        assert "src" in output

    def test_md_short_combo(self, sample_tree: Path) -> None:
        """--md + --short output must be valid Markdown with code block."""
        output = _run_cli_for_root(sample_tree, ["--md", "--short"])
        _assert_md_wrapped(output, "short")

    def test_md_compat_combo(self, sample_tree: Path) -> None:
        """--md without --short wraps compat output."""
        output = _run_cli_for_root(sample_tree, ["--md"])
        _assert_md_wrapped(output, "compat")
        assert "├── " in output or "|-- " in output

    def test_md_short_budget_combo(self, sample_tree: Path) -> None:
        """--md + --short + --budget shows budget in metadata."""
        output = _run_cli_for_root(sample_tree, ["--md", "--short", "--budget", "200"])
        assert "- budget: 200" in output
        _assert_md_wrapped(output, "short")

    def test_short_level_invalid_zero(self, tmp_path: Path) -> None:
        """--short + -L 0 must raise NtreeError."""
        with pytest.raises(NtreeError, match="Invalid level"):
            _run_cli_for_root(tmp_path, ["--short", "-L", "0"])

    def test_preset_and_exclude_combine(self, noisy_tree: Path) -> None:
        """--preset + -I must both apply (union of exclusions)."""
        output = _run_cli_for_root(
            noisy_tree,
            ["--short", "--preset", "node", "-I", "src", "-a"],
        )
        assert "node_modules" not in output  # from preset
        assert "src" not in output  # from -I
