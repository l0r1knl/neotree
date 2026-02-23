"""Golden tests for CSV output."""

from __future__ import annotations

from pathlib import Path

import pytest

from neotree.cli import run_ntree
from tests.conftest import assert_golden


def _csv_output(root: Path, cli_args: list[str]) -> str:
    raw = run_ntree([str(root), *cli_args])
    # Normalize fullpaths to relative for golden comparison portability
    return _normalize_paths(raw, root)


def _normalize_paths(output: str, root: Path) -> str:
    """Replace absolute root prefix in fullpath column with '<ROOT>'.

    This makes golden files portable across machines and OS path styles.
    """
    root_str = str(root)
    return output.replace(root_str, "<ROOT>")


class TestCsvGolden:
    @pytest.mark.parametrize(
        ("root_fixture_name", "cli_args", "golden_name"),
        [
            ("sample_tree", ["--csv"], "csv_basic"),
            ("sample_tree", ["--csv", "-F"], "csv_files_only"),
            ("sample_tree", ["--csv", "-L", "1"], "csv_depth1"),
            ("sample_tree", ["--csv", "-I", "tests"], "csv_exclude_tests"),
            ("noisy_tree", ["--csv", "--preset", "python"], "csv_preset_python"),
        ],
    )
    def test_csv_golden_matrix(
        self,
        request: pytest.FixtureRequest,
        root_fixture_name: str,
        cli_args: list[str],
        golden_name: str,
    ) -> None:
        root = request.getfixturevalue(root_fixture_name)
        output = _csv_output(root, cli_args)
        assert_golden(output, golden_name)
