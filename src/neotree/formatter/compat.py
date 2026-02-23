"""Tree-compatible box-drawing output formatter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from neotree.scanner import Entry


@dataclass(frozen=True, slots=True)
class Glyphs:
    """Box-drawing character set for tree rendering."""

    branch: str  # ├──
    last_branch: str  # └──
    vertical: str  # │
    space: str  # (indent)


UNICODE_GLYPHS = Glyphs(
    branch="├── ",
    last_branch="└── ",
    vertical="│   ",
    space="    ",
)

ASCII_GLYPHS = Glyphs(
    branch="|-- ",
    last_branch="\\-- ",
    vertical="|   ",
    space="    ",
)


@dataclass(frozen=True, slots=True)
class CompatOptions:
    """Options for compat formatter.

    Attributes:
        charset: Output charset, ``unicode`` or ``ascii``.
        dirs_first: Whether directories are sorted before files.
        full_path: Whether to print path from root for each entry.
        no_report: Whether to omit summary report line.
        root_path: Root path used for full path rendering.
    """

    charset: Literal["unicode", "ascii"] = "unicode"
    dirs_first: bool = False
    full_path: bool = False
    no_report: bool = False
    root_path: Path | None = None
    order: Literal["asc", "desc"] = "asc"


def _group_by_parent(entries: list[Entry]) -> dict[Path, list[Entry]]:
    """Group entries by parent path preserving insertion order.

    Args:
        entries: Scanner output entries.

    Returns:
        dict[Path, list[Entry]]: Parent to children mapping.
    """
    groups: dict[Path, list[Entry]] = {}
    for entry in entries:
        groups.setdefault(entry.parent_path, []).append(entry)
    return groups


def _sort_children(
    children: list[Entry], dirs_first: bool, reverse: bool = False
) -> list[Entry]:
    """Sort children according to current compat options.

    Args:
        children: Child entries under one parent.
        dirs_first: Whether to sort directories before files.
        reverse: Whether to sort in descending order.

    Returns:
        list[Entry]: Sorted child entries.
    """
    if dirs_first:
        dirs = sorted(
            [e for e in children if e.is_dir], key=lambda e: e.name, reverse=reverse
        )
        files = sorted(
            [e for e in children if not e.is_dir],
            key=lambda e: e.name,
            reverse=reverse,
        )
        return dirs + files
    return sorted(children, key=lambda e: e.name, reverse=reverse)


def _report_line(dir_count: int, file_count: int) -> str:
    """Build GNU tree-like summary line.

    Args:
        dir_count: Number of directories.
        file_count: Number of files.

    Returns:
        str: Summary string with singular/plural inflection.
    """
    dir_word = "directory" if dir_count == 1 else "directories"
    file_word = "file" if file_count == 1 else "files"
    return f"{dir_count} {dir_word}, {file_count} {file_word}"


def format_compat(
    entries: list[Entry],
    options: CompatOptions | None = None,
) -> str:
    """Render entries as tree-compatible box-drawing text.

    Args:
        entries: Scanner entries to render.
        options: Compat rendering options.

    Returns:
        str: Full output including root line and optional summary report.
    """
    opts = options or CompatOptions()
    glyphs = ASCII_GLYPHS if opts.charset == "ascii" else UNICODE_GLYPHS

    root_display = "."
    if opts.root_path is not None:
        root_display = str(opts.root_path)

    lines: list[str] = [root_display]

    if not entries:
        if not opts.no_report:
            lines.append("")
            lines.append(_report_line(0, 0))
        return "\n".join(lines)

    groups = _group_by_parent(entries)

    root_parent = entries[0].parent_path
    dir_count = 0
    file_count = 0

    reverse = opts.order == "desc"

    # Iterative DFS using an explicit stack.
    # Stack items: (entry, prefix, is_last_sibling)
    # Push children in reverse order so that the first child is popped first.
    root_children = _sort_children(
        groups.get(root_parent, []), opts.dirs_first, reverse
    )
    stack: list[tuple[Entry, str, bool]] = []
    for i in range(len(root_children) - 1, -1, -1):
        stack.append((root_children[i], "", i == len(root_children) - 1))

    while stack:
        child, prefix, is_last = stack.pop()
        connector = glyphs.last_branch if is_last else glyphs.branch

        display_name = child.name
        if opts.full_path:
            try:
                display_name = str(
                    child.path.relative_to(opts.root_path or root_parent)
                )
            except ValueError:
                display_name = str(child.path)

        if child.is_dir:
            display_name += "/"
            dir_count += 1
        else:
            file_count += 1

        lines.append(f"{prefix}{connector}{display_name}")

        if child.is_dir:
            next_prefix = prefix + (glyphs.space if is_last else glyphs.vertical)
            grandchildren = _sort_children(
                groups.get(child.path, []), opts.dirs_first, reverse
            )
            for j in range(len(grandchildren) - 1, -1, -1):
                stack.append(
                    (grandchildren[j], next_prefix, j == len(grandchildren) - 1)
                )

    if not opts.no_report:
        lines.append("")
        lines.append(_report_line(dir_count, file_count))

    return "\n".join(lines)
