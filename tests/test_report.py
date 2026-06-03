"""Tests for output formatting: human, JSON, and keep-manifest."""

from __future__ import annotations

import json
from pathlib import Path

from predupe.cluster import Cluster
from predupe.report import render_human, render_json, write_manifest
from predupe.scan import ScanResult


def _result_with_dupes() -> ScanResult:
    clusters = [Cluster(members=["a.md", "b.md"], similarity=0.97)]
    return ScanResult(
        total_files=3,
        clusters=clusters,
        all_paths=["a.md", "b.md", "c.md"],
    )


def _result_no_dupes() -> ScanResult:
    return ScanResult(total_files=2, clusters=[], all_paths=["x.md", "y.md"])


def test_render_human_lists_clusters_and_summary():
    out = render_human(_result_with_dupes(), color=False)
    assert "DUPLICATE CLUSTERS" in out
    assert "cluster 1" in out
    assert "a.md" in out and "b.md" in out
    assert "3 files -> 2 unique" in out
    assert "1 redundant" in out


def test_render_human_no_dupes_message():
    out = render_human(_result_no_dupes(), color=False)
    assert "No near-duplicates found." in out
    assert "2 files scanned" in out


def test_render_human_color_adds_ansi_codes():
    plain = render_human(_result_with_dupes(), color=False)
    colored = render_human(_result_with_dupes(), color=True)
    assert "\033[" not in plain
    assert "\033[" in colored


def test_render_json_is_valid_and_complete():
    payload = json.loads(render_json(_result_with_dupes()))
    assert payload["total_files"] == 3
    assert payload["unique_count"] == 2
    assert payload["redundant_count"] == 1
    assert payload["clusters"] == [
        {"similarity": 0.97, "members": ["a.md", "b.md"]}
    ]


def test_write_manifest_lists_files_to_keep(tmp_path: Path):
    manifest = tmp_path / "keep.txt"
    write_manifest(_result_with_dupes(), manifest)
    kept = manifest.read_text(encoding="utf-8").splitlines()
    # b.md is the redundant member of the cluster and is dropped.
    assert kept == ["a.md", "c.md"]
