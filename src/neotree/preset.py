"""Exclusion presets for common project types."""

from __future__ import annotations

from typing import Final

PRESETS: Final[dict[str, list[str]]] = {
    "python": [
        "__pycache__",
        ".venv",
        "*.pyc",
        ".pytest_cache",
        "dist",
        "build",
        "*.egg-info",
    ],
    "node": [
        "node_modules",
        ".next",
        "dist",
        ".cache",
        "coverage",
    ],
    "rust": [
        "target",
    ],
    "generic": [
        ".git",
        ".DS_Store",
        "Thumbs.db",
    ],
}

# generic is always applied
_ALWAYS_APPLIED: Final[list[str]] = ["generic"]


def get_preset_patterns(name: str) -> list[str]:
    """Return exclusion patterns for a named preset.

    The ``generic`` preset is always included in addition to the
    requested preset.

    Args:
        name: Preset name.

    Returns:
        list[str]: Combined exclusion pattern list.

    Raises:
        ValueError: If ``name`` is not a known preset.
    """
    if name not in PRESETS:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Known presets: {known}")

    patterns: list[str] = []
    for always in _ALWAYS_APPLIED:
        if always != name:
            patterns.extend(PRESETS[always])
    patterns.extend(PRESETS[name])
    return patterns
