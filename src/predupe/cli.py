"""Command-line interface for predupe."""

from __future__ import annotations

import argparse
import sys

from .report import render_human, render_json, write_manifest
from .scan import scan


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="predupe",
        description="Find near-duplicate documents before you embed them.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="Scan a folder for near-duplicates.")
    s.add_argument("path", help="Directory to scan (recursively).")
    s.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Approx. Jaccard similarity to treat as duplicate (default 0.85).",
    )
    s.add_argument(
        "-k",
        "--shingle-size",
        type=int,
        default=5,
        help="Words per shingle; smaller is more sensitive (default 5).",
    )
    s.add_argument(
        "--num-perm",
        type=int,
        default=128,
        help="MinHash permutations; higher is more accurate, slower (default 128).",
    )
    s.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    s.add_argument(
        "--keep-manifest",
        metavar="FILE",
        help="Write the list of files to keep to FILE.",
    )
    s.add_argument(
        "--fail-on-dupes",
        action="store_true",
        help="Exit with code 1 if any near-duplicates are found (for CI).",
    )
    s.add_argument(
        "--no-color", action="store_true", help="Disable colored output."
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "scan":
        try:
            result = scan(
                args.path,
                k=args.shingle_size,
                threshold=args.threshold,
                num_perm=args.num_perm,
            )
        except FileNotFoundError:
            print(f"error: path not found: {args.path}", file=sys.stderr)
            return 2

        if args.keep_manifest:
            write_manifest(result, args.keep_manifest)

        if args.json:
            print(render_json(result))
        else:
            color = sys.stdout.isatty() and not args.no_color
            print(render_human(result, color=color))

        if args.fail_on_dupes and result.clusters:
            return 1
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
