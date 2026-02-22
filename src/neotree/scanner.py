"""Core directory scanner using os.scandir with explicit stack (DFS)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Entry:
    """A single filesystem entry discovered during scanning.

    Attributes:
        path: Absolute path of the filesystem entry.
        name: Basename of the entry.
        is_dir: Whether the entry is a directory.
        depth: Parent directory depth from scanning root.
        parent_path: Absolute parent directory path.
    """

    path: Path
    name: str
    is_dir: bool
    depth: int
    parent_path: Path


@dataclass(frozen=True, slots=True)
class ScanOptions:
    """Options controlling scanner behavior.

    Attributes:
        max_depth: Maximum parent depth to scan. ``None`` means unlimited.
        dirs_only: Whether to include only directories.
        all_files: Whether to include hidden entries.
    """

    max_depth: int | None = None
    dirs_only: bool = False
    all_files: bool = False


class EntryFilter(Protocol):
    """Protocol for entry filtering.

    Keeps scanner logic decoupled from matching strategy.
    """

    def should_exclude(self, name: str, is_dir: bool) -> bool: ...


class _NullFilter:
    """Default pass-through filter that excludes nothing."""

    def should_exclude(self, name: str, is_dir: bool) -> bool:
        return False


def scan(
    root: Path,
    options: ScanOptions | None = None,
    entry_filter: EntryFilter | None = None,
) -> list[Entry]:
    """Scan root directory and return entries in deterministic DFS order.

    Args:
        root: Root directory to scan.
        options: Scanner options. Defaults to ``ScanOptions()``.
        entry_filter: Optional exclude filter implementation.

    Returns:
        list[Entry]: Flat list of discovered entries.
    """
    scan_options = options or ScanOptions()
    active_filter = entry_filter or _NullFilter()
    root = root.resolve()

    if not root.is_dir():
        return []

    result: list[Entry] = []

    # Stack items: (directory_path, depth)
    # We push directories in reversed sorted order so that
    # the first entry (alphabetically) is popped first.
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        current_dir, depth = stack.pop()

        # Depth limit check: don't scan children beyond max_depth
        if scan_options.max_depth is not None and depth > scan_options.max_depth:
            continue

        try:
            raw_entries = list(os.scandir(current_dir))
        except PermissionError:
            logger.debug("Permission denied: %s", current_dir)
            continue

        # Sort entries by name for deterministic output
        raw_entries.sort(key=lambda e: e.name)

        child_dirs: list[tuple[Path, int]] = []

        for dir_entry in raw_entries:
            name = dir_entry.name
            try:
                is_dir = dir_entry.is_dir(follow_symlinks=False)
            except OSError:
                logger.debug("Cannot stat: %s", dir_entry.path)
                continue

            # Hidden file filtering (unless -a)
            if not scan_options.all_files and name.startswith("."):
                continue

            if active_filter.should_exclude(name, is_dir):
                continue

            if scan_options.dirs_only and not is_dir:
                continue

            entry = Entry(
                path=Path(dir_entry.path),
                name=name,
                is_dir=is_dir,
                depth=depth,
                parent_path=current_dir,
            )
            result.append(entry)

            if is_dir:
                child_dirs.append((Path(dir_entry.path), depth + 1))

        # Push children in reverse so first-alphabetical is popped first
        for child in reversed(child_dirs):
            stack.append(child)

    return result
