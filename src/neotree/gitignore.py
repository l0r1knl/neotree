"""Gitignore integration — load .gitignore patterns via pathspec."""

from __future__ import annotations

import logging
from pathlib import Path

from pathspec import GitIgnoreSpec

logger = logging.getLogger(__name__)


def load_gitignore_spec(root: Path) -> GitIgnoreSpec | None:
    """Load .gitignore patterns from *root* directory.

    Args:
        root: Directory containing the ``.gitignore`` file.

    Returns:
        A compiled spec when a ``.gitignore`` exists and is readable,
        otherwise ``None``.
    """
    gitignore_path = root / ".gitignore"
    try:
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        logger.debug("Cannot read .gitignore: %s", gitignore_path)
        return None
    return GitIgnoreSpec.from_lines(lines)
