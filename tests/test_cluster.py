"""Tests for normalization and clustering."""

from __future__ import annotations

from pathlib import Path

from predupe.cluster import Document, build_minhash, cluster_documents
from predupe.normalize import normalize, shingles
from predupe.scan import scan


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  Hello   WORLD\n\n") == "hello world"


def test_normalize_strips_html():
    html = "<p>Hello <b>world</b></p><script>ignore()</script>"
    assert "ignore" not in normalize(html, is_html=True)
    assert "hello world" in normalize(html, is_html=True)


def test_shingles_short_doc():
    assert shingles("one two", k=5) == {"one two"}


def test_identical_docs_cluster():
    text = "the quick brown fox jumps over the lazy dog " * 5
    docs = [Document(path=f"f{i}", text=normalize(text)) for i in range(3)]
    clusters = cluster_documents(docs, threshold=0.8)
    assert len(clusters) == 1
    assert sorted(clusters[0].members) == ["f0", "f1", "f2"]


def test_distinct_docs_do_not_cluster():
    docs = [
        Document(path="a", text=normalize("apples oranges pears grapes melons")),
        Document(path="b", text=normalize("trucks planes trains boats rockets")),
    ]
    clusters = cluster_documents(docs, threshold=0.5)
    assert clusters == []


def test_near_duplicate_clusters():
    base = "machine learning models require careful evaluation and testing here"
    edited = base.replace("testing", "validation")
    docs = [
        Document(path="orig", text=normalize(base)),
        Document(path="edit", text=normalize(edited)),
    ]
    clusters = cluster_documents(docs, k=3, threshold=0.5)
    assert len(clusters) == 1


def test_scan_end_to_end(tmp_path: Path):
    (tmp_path / "a.md").write_text("shared content that is duplicated across files")
    (tmp_path / "b.md").write_text("shared content that is duplicated across files")
    (tmp_path / "c.md").write_text("completely different unique text over here now")
    result = scan(tmp_path, threshold=0.7)
    assert result.total_files == 3
    assert result.redundant_count == 1
    assert result.unique_count == 2
    keep = result.keep_list()
    assert len(keep) == 2


def test_empty_files_are_not_treated_as_duplicates():
    # An empty MinHash matches every other empty MinHash at Jaccard 1.0, so
    # empty/whitespace-only files must be excluded from clustering rather than
    # collapsed into one bogus "duplicate" cluster (which would drop real files
    # from a keep-manifest).
    docs = [
        Document(path="empty", text=normalize("")),
        Document(path="blank", text=normalize("   \n\n  ")),
        Document(path="real", text=normalize("some actual content lives here")),
    ]
    clusters = cluster_documents(docs, threshold=0.7)
    assert clusters == []


def test_scan_keeps_empty_files(tmp_path: Path):
    (tmp_path / "empty1.md").write_text("")
    (tmp_path / "empty2.md").write_text("   \n  ")
    (tmp_path / "real.md").write_text("a normal document with several words in it")
    result = scan(tmp_path, threshold=0.7)
    assert result.redundant_count == 0
    assert sorted(result.keep_list()) == sorted(result.all_paths)


def test_clustering_is_deterministic():
    # Same input must yield identical clusters across runs (pinned seed) so CI
    # results are reproducible.
    text = "the quick brown fox jumps over the lazy dog and runs away fast"
    docs1 = [Document(path=f"f{i}", text=normalize(text)) for i in range(3)]
    docs2 = [Document(path=f"f{i}", text=normalize(text)) for i in range(3)]
    c1 = cluster_documents(docs1, k=3, threshold=0.8)
    c2 = cluster_documents(docs2, k=3, threshold=0.8)
    assert [(c.members, c.similarity) for c in c1] == [
        (c.members, c.similarity) for c in c2
    ]


def test_build_minhash_honors_seed():
    # Identical text under the same seed -> identical signature (Jaccard 1.0).
    a = build_minhash("alpha beta gamma delta", k=2, num_perm=64, seed=7)
    b = build_minhash("alpha beta gamma delta", k=2, num_perm=64, seed=7)
    assert a.jaccard(b) == 1.0
