# predupe

[![CI](https://github.com/egrilmez/JasCan/actions/workflows/ci.yml/badge.svg)](https://github.com/egrilmez/JasCan/actions/workflows/ci.yml)

**Find near-duplicate documents *before* you embed them.**

`predupe` scans a folder of text, Markdown, reStructuredText, and HTML files and flags duplicates and near-duplicates so you don't waste embedding API calls — and don't pollute your vector store with redundant chunks that hurt retrieval quality. (PDF and DOCX extraction are on the roadmap.)

It works in two stages, cheapest first, so you never pay for a similarity comparison you didn't need.

---

## Why this exists

Every duplicate you embed costs you twice:

1. **Money** — you pay to embed the same content multiple times.
2. **Retrieval quality** — near-identical chunks crowd out diverse results. A query that should surface 5 distinct sources instead returns 5 copies of the same paragraph.

Most RAG pipelines skip dedup entirely, or do a naïve exact-hash check that misses the 95%-identical files (boilerplate headers, re-exported docs, lightly edited versions). `predupe` catches those without a model and without an O(n²) comparison blowup.

---

## How it works

```
files ──► [1] normalize ──► [2] lexical LSH ──► [3] semantic pass ──► report
                             (no model, fast)    (optional, embeddings)
```

1. **Normalize** — strip markup, collapse whitespace, lowercase. Cheap, removes formatting-only differences.
2. **Lexical LSH** — MinHash + Locality-Sensitive Hashing over character/word shingles. Finds exact and near-exact duplicates in roughly linear time, no embeddings needed. This alone catches the majority of real-world dupes (re-exports, boilerplate, copy-paste).
3. **Semantic pass** *(opt-in, `--semantic`)* — only the survivors get embedded with a small local model (`all-MiniLM-L6-v2` by default) and compared via an ANN index (hnswlib) above a cosine threshold. Catches paraphrases and translations that LSH misses.

The point: stage 2 is nearly free and eliminates most candidates, so the expensive stage 3 runs on a fraction of the corpus — or never runs at all if you don't need semantic matching.

---

## Quickstart

```bash
pip install predupe

# Lexical dedup — fast, no downloads, no GPU
predupe scan ./docs

# Tune sensitivity (lower threshold = more aggressive matching)
predupe scan ./docs --threshold 0.92

# CI-friendly: exit non-zero if any near-dupes found
predupe scan ./docs --fail-on-dupes
```

> Semantic detection (`--semantic`) for paraphrases is planned for v0.2 — see the [Roadmap](#roadmap). v0.1 is lexical-only.

Example output:

```
DUPLICATE CLUSTERS
  cluster 1  (3 files, ~0.99 similar)
    docs/archive/setup-old.md
    docs/setup-copy.md
    docs/setup.md
  cluster 2  (2 files, ~0.97 similar)
    docs/api/auth.md
    docs/api/authentication.md

Summary: 1,204 files -> 1,189 unique  (15 redundant)
```

---

## Output formats

- **Human** (default) — clustered, color-coded terminal output.
- **JSON** (`--json`) — machine-readable clusters for piping into your pipeline.
- **Manifest** (`--keep-manifest dedup.txt`) — a flat list of the files to *keep*, so your ingestion step can read it directly:

```bash
predupe scan ./docs --keep-manifest keep.txt
cat keep.txt | your-ingestion-script
```

---

## Architecture notes

- **Streaming, not loading.** Files are read and shingled in a stream; the corpus never has to fit in memory.
- **Parallel.** Normalization and MinHash run across a worker pool; embarrassingly parallel by file.
- **Pluggable embedders.** The semantic pass takes any callable that maps text → vector, so you can swap in your own model or a hosted endpoint.
- **Deterministic.** Same input, same MinHash seed, same clusters — important for reproducible CI.

Core dependencies: `datasketch` (MinHash/LSH), `hnswlib` (ANN), `sentence-transformers` (optional, only pulled in when `--semantic` is used).

---

## Roadmap

**v0.1 — Lexical dedup (the weekend MVP)**
- Recursive folder scan (`.txt`, `.md`, `.html`)
- Normalization + MinHash/LSH clustering
- Human + JSON output, keep-manifest
- Tunable shingle size and Jaccard threshold

**v0.2 — Semantic pass**
- Opt-in local embedding + hnswlib near-neighbor search
- Cosine threshold flag
- Cost-avoided estimator

**v0.3 — Pipeline integration**
- PDF and DOCX extraction
- `--fail-on-dupes` for CI
- Chunk-level dedup (not just whole-file) for already-chunked corpora

**Later**
- Incremental mode (only scan files changed since last run, persist the LSH index)
- Vector-store connectors (dedup against what's *already* indexed)

---

## Contributing

v0.1 is intentionally small — a good first PR is a new file-type extractor or an output format. Open an issue before large changes so we can keep the surface area tight.

## License

MIT
