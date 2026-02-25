"""CSV output formatter for ntree.

Design for extensibility
------------------------
This module defines a ``CsvColumn`` protocol that decouples column *definition*
from column *extraction*.  Future metadata columns (e.g. page_count for PDFs,
word_count for Word documents, sheet_count for Excel files) can be added by
implementing a new ``CsvColumn`` instance and appending it to the column list
passed to ``format_csv``.

Example of a future metadata column (not yet implemented)::

    page_count_column = CsvColumn(
        name="page_count",
        extract=lambda entry, root: _pdf_page_count(entry.path),
    )

The ``--csv-columns`` CLI option (future) will allow users to select which
columns to include at runtime.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from typing import Callable, Literal

from neotree.scanner import Entry


@dataclass(frozen=True, slots=True)
class CsvColumn:
    """A single CSV output column.

    Attributes:
        name: Header name for this column.
        extract: Callable that takes ``(entry, root)`` and returns a string
            value.  ``root`` is the scan root path, useful for computing
            relative paths or contextual information.

    Future usage::

        CsvColumn(
            name="page_count",
            extract=lambda entry, root: str(_pdf_pages(entry.path)),
        )
    """

    name: str
    extract: Callable[[Entry, Path], str]


def _extract_parent_dir(entry: Entry, root: Path) -> str:  # noqa: ARG001
    """Return the immediate parent directory name.

    For entries directly under root, returns the root directory name
    (not an empty string), which is the most intuitive representation.
    """
    return entry.parent_path.name


def _extract_filename(entry: Entry, root: Path) -> str:  # noqa: ARG001
    return entry.name


def _extract_fullpath(entry: Entry, root: Path) -> str:  # noqa: ARG001
    return str(entry.path)


def _extract_depth(entry: Entry, root: Path) -> str:  # noqa: ARG001
    return str(entry.depth)


# Default column set for v1. Future: user-selectable via --csv-columns.
DEFAULT_COLUMNS: list[CsvColumn] = [
    CsvColumn(name="parent_dir", extract=_extract_parent_dir),
    CsvColumn(name="filename", extract=_extract_filename),
    CsvColumn(name="fullpath", extract=_extract_fullpath),
    CsvColumn(name="depth", extract=_extract_depth),
]


@dataclass(frozen=True, slots=True)
class CsvOptions:
    """Options controlling CSV output.

    Attributes:
        root_path: Root path used for path computation. Required for
            meaningful ``parent_dir`` values.
        files_only: When ``True``, directory rows are excluded from output
            (files inside subdirectories are still included).
        columns: Column definitions to use. Defaults to ``DEFAULT_COLUMNS``.
            Pass a custom list to add or reorder columns (future use via
            ``--csv-columns``).
        order: Sort direction within each parent group, ``asc`` or ``desc``.
    """

    root_path: Path | None = None
    files_only: bool = False
    columns: list[CsvColumn] = field(default_factory=lambda: list(DEFAULT_COLUMNS))
    order: Literal["asc", "desc"] = "asc"


def format_csv(
    entries: list[Entry],
    options: CsvOptions | None = None,
) -> str:
    """Render entries as CSV text.

    Output always starts with a header row.  Each subsequent row represents
    one filesystem entry.

    Rules:
      1. Header columns match ``options.columns`` order.
      2. When ``options.files_only`` is ``True``, directory entries are
         skipped (traversal already happened at scan time; this filter applies
         to any directory entries that remain in the list).
      3. ``fullpath`` uses the OS-native path separator (``Path`` handles
         this automatically).
      4. ``depth`` is 0-based from the scan root.

    Args:
        entries: Scanner entries to render.
        options: Rendering options.  Defaults to ``CsvOptions()``.

    Returns:
        str: CSV text with header, using LF line endings (no trailing newline).
    """
    opts = options or CsvOptions()
    root = opts.root_path or (entries[0].parent_path if entries else Path("."))
    columns = opts.columns

    # For desc order, re-sort within each parent group.
    # Same-parent entries are always contiguous in DFS scan output.
    effective_entries: list[Entry]
    if opts.order == "desc":
        effective_entries = []
        for _, grp in groupby(entries, key=lambda e: e.parent_path):
            effective_entries.extend(sorted(grp, key=lambda e: e.name, reverse=True))
    else:
        effective_entries = entries

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")

    writer.writerow([col.name for col in columns])

    for entry in effective_entries:
        if opts.files_only and entry.is_dir:
            continue
        writer.writerow([col.extract(entry, root) for col in columns])

    # Remove trailing newline that csv.writer appends after the last row
    return buf.getvalue().rstrip("\n")
