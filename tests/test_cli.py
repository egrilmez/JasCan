"""Tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from predupe.cli import main


def _make_corpus(root: Path) -> None:
    (root / "a.md").write_text("shared content that is duplicated across files")
    (root / "b.md").write_text("shared content that is duplicated across files")
    (root / "c.md").write_text("completely different unique text over here now")


def test_scan_reports_dupes_and_exits_zero(tmp_path: Path, capsys):
    _make_corpus(tmp_path)
    code = main(["scan", str(tmp_path), "--threshold", "0.7", "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "DUPLICATE CLUSTERS" in out


def test_json_output_is_machine_readable(tmp_path: Path, capsys):
    _make_corpus(tmp_path)
    code = main(["scan", str(tmp_path), "--threshold", "0.7", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["total_files"] == 3
    assert payload["redundant_count"] == 1


def test_fail_on_dupes_returns_one(tmp_path: Path):
    _make_corpus(tmp_path)
    code = main(["scan", str(tmp_path), "--threshold", "0.7", "--fail-on-dupes"])
    assert code == 1


def test_fail_on_dupes_returns_zero_when_clean(tmp_path: Path):
    (tmp_path / "only.md").write_text("a single solitary unique document here")
    code = main(["scan", str(tmp_path), "--fail-on-dupes"])
    assert code == 0


def test_keep_manifest_is_written(tmp_path: Path):
    _make_corpus(tmp_path)
    manifest = tmp_path / "keep.txt"
    main(
        [
            "scan",
            str(tmp_path),
            "--threshold",
            "0.7",
            "--keep-manifest",
            str(manifest),
        ]
    )
    kept = manifest.read_text(encoding="utf-8").splitlines()
    assert len(kept) == 2  # 3 files, 1 redundant dropped


def test_missing_path_returns_two(tmp_path: Path, capsys):
    code = main(["scan", str(tmp_path / "does-not-exist")])
    err = capsys.readouterr().err
    assert code == 2
    assert "path not found" in err


def test_no_command_errors(capsys):
    # argparse requires a subcommand; it exits rather than returning.
    with pytest.raises(SystemExit):
        main([])
