"""Entry filtering: fnmatch-based exclusion and hidden-file logic."""

from __future__ import annotations

from fnmatch import fnmatch


class PatternFilter:
    """Filter entries by fnmatch patterns.

    Implements ``-I PATTERN`` exclusion behavior.
    """

    def __init__(self, patterns: list[str] | None = None) -> None:
        """Initialize pattern filter.

        Args:
            patterns: Optional fnmatch pattern list.
        """
        self._patterns: list[str] = list(patterns) if patterns else []

    def should_exclude(self, name: str, is_dir: bool) -> bool:
        """Return whether an entry should be excluded.

        Args:
            name: Entry name.
            is_dir: Whether the entry is a directory.

        Returns:
            bool: ``True`` when any configured pattern matches.
        """
        return any(fnmatch(name, pat) for pat in self._patterns)
