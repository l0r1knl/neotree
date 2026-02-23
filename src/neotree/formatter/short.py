"""Short grouped output formatter."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from neotree.scanner import Entry


@dataclass(frozen=True, slots=True)
class ShortOptions:
    """Options for short grouped output.

    Attributes:
        budget: Approximate character budget for output aggregation.
        count: Whether to include per-group file counts.
        root_path: Root path used for relative path rendering.
    """

    budget: int | None = None
    count: bool = False
    root_path: Path | None = None
    order: Literal["asc", "desc"] = "asc"


def _build_relative_dir_key(entry_parent: Path, root: Path) -> str:
    """Return a display-friendly directory key relative to root.

    Args:
        entry_parent: Parent path of an entry.
        root: Root path for relative conversion.

    Returns:
        str: Relative display key, or absolute-like fallback on mismatch.
    """
    try:
        rel = entry_parent.relative_to(root)
    except ValueError:
        return str(entry_parent)
    return str(rel).replace("\\", "/") if str(rel) != "." else "."


def _group_entries_by_parent(
    entries: list[Entry],
    root: Path,
) -> OrderedDict[str, list[Entry]]:
    """Group entries by parent directory key.

    Directories without children are represented as standalone keys ending
    with ``/``.

    Args:
        entries: Scanner entries in stable traversal order.
        root: Root path used for relative directory keys.

    Returns:
        OrderedDict[str, list[Entry]]: Grouped entries by display directory key.
    """
    groups: OrderedDict[str, list[Entry]] = OrderedDict()
    dir_paths_with_children: set[str] = set()

    # First pass: record which directories have children
    for entry in entries:
        parent_rel = _build_relative_dir_key(entry.parent_path, root)
        dir_paths_with_children.add(parent_rel)

    for entry in entries:
        parent_key = _build_relative_dir_key(entry.parent_path, root)

        if entry.is_dir:
            # Check if this dir has children (appears as a parent_key)
            try:
                dir_rel = str(entry.path.relative_to(root)).replace("\\", "/")
            except ValueError:
                dir_rel = str(entry.path)
            if dir_rel not in dir_paths_with_children:
                # Childless dir: standalone line
                groups.setdefault(dir_rel + "/", [])
            # Don't add the dir itself as a file entry
            continue

        groups.setdefault(parent_key, []).append(entry)

    return groups


def _format_group_line(
    dir_key: str,
    files: list[Entry],
    count: bool,
) -> str:
    """Format one grouped output line.

    Args:
        dir_key: Directory display key.
        files: Files contained in the group.
        count: Whether to include ``(files: N)``.

    Returns:
        str: Formatted line for grouped output.
    """
    file_names = ", ".join(e.name for e in files)

    if not files:
        # Childless directory
        if count:
            return f"{dir_key}"
        return dir_key

    if count:
        return f"{dir_key} (files: {len(files)}): {file_names}"

    return f"{dir_key}: {file_names}"


def _aggregate_deep_groups(
    groups: OrderedDict[str, list[Entry]],
    budget: int,
    count: bool,
) -> list[str]:
    """Aggregate deep groups first when output exceeds budget.

    Args:
        groups: Grouped entries keyed by directory display string.
        budget: Maximum approximate output character count.
        count: Whether non-aggregated lines include file counts.

    Returns:
        list[str]: Final formatted lines after required aggregation.
    """
    overrides: dict[str, str] = {}

    def _build_lines() -> list[str]:
        result = []
        for k, v in groups.items():
            if k in overrides:
                result.append(overrides[k])
            else:
                result.append(_format_group_line(k, v, count))
        return result

    def _lines_length(lines: list[str]) -> int:
        return sum(len(line) for line in lines) + len(lines)

    lines = _build_lines()
    total = _lines_length(lines)

    if total <= budget:
        return lines

    # Sort group keys by depth (deepest first) for aggregation candidates
    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: k.count("/"),
        reverse=True,
    )

    for key in sorted_keys:
        lines = _build_lines()
        if _lines_length(lines) <= budget:
            break

        # Skip already-aggregated or childless (empty) groups
        if key in overrides or not groups[key]:
            continue

        n_files = len(groups[key])
        clean_key = key.rstrip("/")
        overrides[key] = f"{clean_key}/* ({n_files} files)"

    return _build_lines()


def format_short(
    entries: list[Entry],
    options: ShortOptions | None = None,
) -> str:
    """Render entries as compact grouped text.

    Rules:
      1. No box-drawing — paths only.
      2. Files in the same directory are comma-joined.
      3. Childless directories get their own line.
      4. ``--budget N`` triggers deep→shallow aggregation.
      5. ``--count`` appends ``(files: N)`` per group.

    Args:
        entries: Scanner entries to render.
        options: Rendering options for short mode.

    Returns:
        str: Newline-joined grouped output.
    """
    opts = options or ShortOptions()
    root = opts.root_path or (entries[0].parent_path if entries else Path("."))

    if not entries:
        return ""

    groups = _group_entries_by_parent(entries, root)

    if opts.order == "desc":
        for files in groups.values():
            files.sort(key=lambda e: e.name, reverse=True)

    if opts.budget is not None:
        lines = _aggregate_deep_groups(groups, opts.budget, opts.count)
    else:
        lines = [_format_group_line(k, v, opts.count) for k, v in groups.items()]

    return "\n".join(lines)
