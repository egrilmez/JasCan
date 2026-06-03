"""Output formatting: human-readable, JSON, and keep-manifest."""

from __future__ import annotations

import json
from pathlib import Path

from .scan import ScanResult


def _color(text: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text


def render_human(result: ScanResult, *, color: bool = True) -> str:
    lines: list[str] = []
    if not result.clusters:
        lines.append(
            _color("No near-duplicates found.", "32", color)
            + f"  ({result.total_files} files scanned)"
        )
        return "\n".join(lines)

    lines.append(_color("DUPLICATE CLUSTERS", "1;33", color))
    for n, c in enumerate(result.clusters, 1):
        head = (
            f"  cluster {n}  ({len(c.members)} files, "
            f"~{c.similarity:.2f} similar)"
        )
        lines.append(_color(head, "33", color))
        for path in c.members:
            lines.append(f"    {path}")
    lines.append("")
    summary = (
        f"Summary: {result.total_files} files -> {result.unique_count} unique  "
        f"({result.redundant_count} redundant)"
    )
    lines.append(_color(summary, "1", color))
    return "\n".join(lines)


def render_json(result: ScanResult) -> str:
    payload = {
        "total_files": result.total_files,
        "unique_count": result.unique_count,
        "redundant_count": result.redundant_count,
        "clusters": [
            {"similarity": round(c.similarity, 4), "members": c.members}
            for c in result.clusters
        ],
    }
    return json.dumps(payload, indent=2)


def write_manifest(result: ScanResult, path: str | Path) -> None:
    """Write the list of files to KEEP (one per line)."""
    keep = result.keep_list()
    Path(path).write_text("\n".join(keep) + "\n", encoding="utf-8")
