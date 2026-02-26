"""Shared fixtures for neotree tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Create a standard test directory tree.

    Structure::

        root/
        ├── docs/
        │   └── guide.md
        ├── src/
        │   ├── api/
        │   │   ├── auth.py
        │   │   └── user.py
        │   └── models/
        │       └── user.py
        ├── tests/
        │   └── test_user.py
        └── README.md
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "api").mkdir()
    (tmp_path / "src" / "api" / "auth.py").write_text("auth")
    (tmp_path / "src" / "api" / "user.py").write_text("user")
    (tmp_path / "src" / "models").mkdir()
    (tmp_path / "src" / "models" / "user.py").write_text("user")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_user.py").write_text("test")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


@pytest.fixture
def noisy_tree(tmp_path: Path) -> Path:
    """Tree with noise directories (node_modules, __pycache__, etc.).

    Structure::

        root/
        ├── node_modules/
        │   └── pkg/
        │       └── index.js
        ├── src/
        │   ├── app.py
        │   └── __pycache__/
        │       └── app.cpython-313.pyc
        ├── .venv/
        │   └── bin/
        │       └── activate
        └── README.md
    """
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("js")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "src" / "__pycache__" / "app.cpython-313.pyc").write_bytes(b"\x00")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "activate").write_text("activate")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


@pytest.fixture
def gitignore_tree(tmp_path: Path) -> Path:
    """Tree with .gitignore for gitignore-integration testing.

    Structure::

        root/
        ├── .gitignore          (*.pyc, node_modules/, dist/)
        ├── dist/
        │   └── bundle.js
        ├── node_modules/
        │   └── pkg/
        │       └── index.js
        ├── src/
        │   ├── app.py
        │   └── app.pyc
        └── README.md
    """
    (tmp_path / ".gitignore").write_text("*.pyc\nnode_modules/\ndist/\n")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("bundle")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("js")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app")
    (tmp_path / "src" / "app.pyc").write_bytes(b"\x00")
    (tmp_path / "README.md").write_text("readme")
    return tmp_path


GOLDEN_DIR = Path(__file__).parent / "golden"


def _golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.txt"


def assert_golden(output: str, name: str) -> None:
    """Compare output against a golden file.

    Set ``UPDATE_GOLDEN=true`` in the environment to regenerate golden files.
    """
    golden_file = _golden_path(name)
    update = os.environ.get("UPDATE_GOLDEN", "").lower() in ("1", "true")

    if update or not golden_file.exists():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        golden_file.write_text(output, encoding="utf-8", newline="")
        if not update:
            pytest.fail(
                f"Golden file '{golden_file.name}' did not exist — created. "
                f"Re-run the test to verify."
            )
        return

    expected = golden_file.read_text(encoding="utf-8")
    assert output == expected, (
        f"Output differs from golden file '{golden_file.name}'.\n"
        f"Run with UPDATE_GOLDEN=true to regenerate."
    )
