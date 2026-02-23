"""CLI entry point for ntree — I/O boundary only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neotree import NtreeError
from neotree.filter import PatternFilter
from neotree.formatter.compat import CompatOptions, format_compat
from neotree.scanner import Entry, ScanOptions, scan


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser for the ``ntree`` command.
    """
    parser = argparse.ArgumentParser(
        prog="ntree",
        description="tree-compatible structure viewer with compact grouped output",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to display (default: current directory)",
    )

    # tree-compat options
    parser.add_argument(
        "-L",
        "--level",
        type=int,
        default=None,
        dest="max_depth",
        help="Max display depth of the directory tree",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        dest="all_files",
        help="Include hidden files (starting with .)",
    )
    parser.add_argument(
        "-d",
        "--dirs-only",
        action="store_true",
        dest="dirs_only",
        help="List directories only",
    )
    parser.add_argument(
        "-I",
        "--exclude",
        action="append",
        default=[],
        dest="patterns",
        help="Exclude entries matching pattern (can be specified multiple times)",
    )
    parser.add_argument(
        "--dirsfirst",
        action="store_true",
        dest="dirs_first",
        help="List directories before files",
    )
    parser.add_argument(
        "--noreport",
        action="store_true",
        dest="no_report",
        help="Omit the file/directory count report at the end",
    )
    parser.add_argument(
        "-f",
        "--fullpath",
        action="store_true",
        dest="full_path",
        help="Print the full path prefix for each entry",
    )
    parser.add_argument(
        "--charset",
        choices=["unicode", "ascii"],
        default="unicode",
        help="Character set for tree drawing (default: unicode)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        dest="output_file",
        help="Write output to a file instead of stdout",
    )

    # neotree extension options
    parser.add_argument(
        "--short",
        action="store_true",
        dest="short_mode",
        help="Compact grouped output by directory",
    )
    parser.add_argument(
        "--md",
        action="store_true",
        dest="md_mode",
        help="Wrap output in Markdown format",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Approximate character budget for --short output",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show file counts per directory in --short mode",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help="Apply exclusion preset (python, node, rust, generic)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        dest="csv_mode",
        help="Output as CSV (parent_dir, filename, fullpath, depth)",
    )
    parser.add_argument(
        "-F",
        "--files-only",
        action="store_true",
        dest="files_only",
        help="Exclude directory entries; show files only (applies to all modes)",
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="asc",
        help="Sort direction: asc (default) or desc",
    )
    return parser


def run_ntree(argv: list[str] | None = None) -> str:
    """Run ntree with provided CLI args and return formatted output.

    This function is intentionally side-effect free and is the primary
    test target for CLI behavior.

    Args:
        argv: Command-line argument list without program name. If ``None``,
            uses process arguments via ``argparse`` defaults.

    Returns:
        str: Final rendered output.

    Raises:
        NtreeError: On any user-facing validation or I/O error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return _run_with_args(args)


def _resolve_root(directory: str) -> Path:
    """Resolve directory and validate it is a directory.

    Args:
        directory: Directory argument from CLI.

    Returns:
        Path: Resolved root path.

    Raises:
        NtreeError: If directory does not exist or is not a directory.
    """
    root = Path(directory).resolve()
    if not root.is_dir():
        raise NtreeError(f"'{directory}' is not a directory")
    return root


def _build_exclude_patterns(args: argparse.Namespace) -> list[str]:
    """Build exclusion patterns from CLI options.

    Args:
        args: Parsed CLI namespace.

    Returns:
        list[str]: Pattern list.

    Raises:
        NtreeError: If ``--preset`` value is invalid.
    """
    patterns: list[str] = list(args.patterns)
    if not args.preset:
        return patterns

    from neotree.preset import get_preset_patterns

    try:
        patterns.extend(get_preset_patterns(args.preset))
    except ValueError as exc:
        raise NtreeError(str(exc)) from exc
    return patterns


def _translate_level_to_scan_depth(level_arg: int | None) -> int | None:
    """Translate ``-L`` level semantics to scanner depth.

    Args:
        level_arg: CLI value of ``-L/--level``.

    Returns:
        int | None: Scanner depth value, or ``None`` when not set.

    Raises:
        NtreeError: If level is less than 1.
    """
    if level_arg is None:
        return None
    if level_arg < 1:
        raise NtreeError("Invalid level, must be greater than 0.")
    return level_arg - 1


def _validate_option_combinations(args: argparse.Namespace) -> None:
    """Validate incompatible CLI option combinations.

    Args:
        args: Parsed CLI namespace.

    Raises:
        NtreeError: If incompatible options are combined.
    """
    if args.short_mode and args.dirs_only:
        raise NtreeError("--short is incompatible with --dirs-only (-d)")
    if not args.short_mode and args.budget is not None:
        raise NtreeError("--budget requires --short")
    if not args.short_mode and args.count:
        raise NtreeError("--count requires --short")
    if args.budget is not None and args.budget < 1:
        raise NtreeError("--budget must be a positive integer")
    if args.csv_mode and args.short_mode:
        raise NtreeError("--csv is incompatible with --short")
    if args.csv_mode and args.md_mode:
        raise NtreeError("--csv is incompatible with --md")
    if args.files_only and args.dirs_only:
        raise NtreeError("--files-only (-F) is incompatible with --dirs-only (-d)")
    if args.files_only and args.short_mode:
        raise NtreeError("--files-only (-F) is incompatible with --short")


def _format_output(args: argparse.Namespace, root: Path, entries: list[Entry]) -> str:
    """Render scanner entries using selected formatter options.

    Args:
        args: Parsed CLI namespace.
        root: Resolved root directory.
        entries: Scanner output list.

    Returns:
        str: Rendered tree output.
    """
    if args.csv_mode:
        from neotree.formatter.csv_ import CsvOptions, format_csv

        csv_opts = CsvOptions(
            root_path=root,
            files_only=args.files_only,
            order=args.order,
        )
        return format_csv(entries, csv_opts)

    if args.short_mode:
        from neotree.formatter.short import ShortOptions, format_short

        short_opts = ShortOptions(
            budget=args.budget,
            count=args.count,
            root_path=root,
            order=args.order,
        )
        return format_short(entries, short_opts)

    compat_opts = CompatOptions(
        charset=args.charset,
        dirs_first=args.dirs_first,
        full_path=args.full_path,
        no_report=args.no_report,
        root_path=root if args.full_path else None,
        order=args.order,
    )
    return format_compat(entries, compat_opts)


def _run_with_args(args: argparse.Namespace) -> str:
    """Run the core scan/format pipeline for parsed arguments.

    Args:
        args: Parsed CLI namespace.

    Returns:
        str: Rendered output.

    Raises:
        NtreeError: On any user-facing validation or I/O error.
    """
    root = _resolve_root(args.directory)
    patterns = _build_exclude_patterns(args)
    scan_max_depth = _translate_level_to_scan_depth(args.max_depth)
    _validate_option_combinations(args)

    entry_filter = PatternFilter(patterns) if patterns else None

    scan_opts = ScanOptions(
        max_depth=scan_max_depth,
        dirs_only=args.dirs_only,
        all_files=args.all_files,
        files_only=args.files_only if not args.csv_mode else False,
    )

    entries = scan(root, scan_opts, entry_filter)
    output = _format_output(args, root, entries)

    if args.md_mode:
        from neotree.formatter.markdown import MdOptions, format_markdown

        md_opts = MdOptions(
            mode="short" if args.short_mode else "compat",
            root=str(root),
            budget=args.budget,
        )
        output = format_markdown(output, md_opts)

    return output


def main() -> None:
    """Run the CLI entry point with process arguments.

    Parses args exactly once and writes output to stdout or ``-o`` file.
    Exits with code 1 on user-facing errors.
    """
    parser = build_parser()
    args = parser.parse_args()  # single parse

    try:
        output = _run_with_args(args)
    except NtreeError as exc:
        sys.stderr.write(f"ntree: {exc}\n")
        sys.exit(1)

    if args.output_file:
        try:
            Path(args.output_file).write_text(
                output + "\n", encoding="utf-8", newline=""
            )
        except OSError as exc:
            sys.stderr.write(f"ntree: cannot write to '{args.output_file}': {exc}\n")
            sys.exit(1)
    else:
        sys.stdout.write(output + "\n")
