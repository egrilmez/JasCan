"""Near-duplicate clustering via MinHash + LSH.

Pipeline:
  1. Build a MinHash signature for each document's shingle set.
  2. Insert signatures into an LSH index keyed by an approximate Jaccard
     threshold. LSH lets us query for "everything probably similar to X"
     without comparing X against every other document (no O(n^2) blowup).
  3. Resolve the resulting pairwise links into clusters with union-find.

The whole thing is deterministic given a fixed `num_perm` and seed, which
matters for reproducible CI runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datasketch import MinHash, MinHashLSH

from .normalize import shingles

# Pinned MinHash permutation seed. MinHash signatures only compare meaningfully
# when they share a seed, and clustering must be reproducible across runs (and
# across machines) for deterministic CI. We set this explicitly rather than
# relying on datasketch's implicit default so the guarantee is part of our API,
# not an upstream coincidence.
DEFAULT_SEED = 1


@dataclass
class Document:
    path: str
    text: str  # normalized
    minhash: MinHash | None = field(default=None, repr=False)


def build_minhash(
    text: str, *, k: int, num_perm: int, seed: int = DEFAULT_SEED
) -> MinHash:
    m = MinHash(num_perm=num_perm, seed=seed)
    for sh in shingles(text, k=k):
        m.update(sh.encode("utf-8"))
    return m


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


@dataclass
class Cluster:
    members: list[str]
    similarity: float  # min pairwise estimate within the cluster


def cluster_documents(
    docs: list[Document],
    *,
    k: int = 5,
    threshold: float = 0.85,
    num_perm: int = 128,
    seed: int = DEFAULT_SEED,
) -> list[Cluster]:
    """Return clusters of near-duplicate documents.

    Only clusters of size >= 2 are returned; unique documents are omitted.
    `threshold` is the approximate Jaccard similarity above which two
    documents are considered duplicates. `seed` pins the MinHash permutations
    so the same input always yields the same clusters.
    """
    if not docs:
        return []

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for i, doc in enumerate(docs):
        if not doc.text.split():
            # Empty / whitespace-only document: it has no shingles to
            # fingerprint, so an empty MinHash would match every other empty
            # MinHash at Jaccard 1.0 and collapse all empty files into one
            # bogus "duplicate" cluster. Skip it; it stays a unique file.
            continue
        doc.minhash = build_minhash(doc.text, k=k, num_perm=num_perm, seed=seed)
        lsh.insert(str(i), doc.minhash)

    uf = _UnionFind(len(docs))
    # Track the weakest link per pair so we can report a similarity figure.
    pair_sim: dict[tuple[int, int], float] = {}
    for i, doc in enumerate(docs):
        if doc.minhash is None:
            continue
        matches = lsh.query(doc.minhash)
        for raw in matches:
            j = int(raw)
            if j <= i:
                continue
            sim = doc.minhash.jaccard(docs[j].minhash)
            pair_sim[(i, j)] = sim
            uf.union(i, j)

    # Gather members by root.
    groups: dict[int, list[int]] = {}
    for i in range(len(docs)):
        groups.setdefault(uf.find(i), []).append(i)

    clusters: list[Cluster] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        sims = [
            pair_sim[(a, b)]
            for a in members
            for b in members
            if a < b and (a, b) in pair_sim
        ]
        similarity = min(sims) if sims else threshold
        clusters.append(
            Cluster(
                members=sorted(docs[m].path for m in members),
                similarity=similarity,
            )
        )

    # Largest, most-similar clusters first.
    clusters.sort(key=lambda c: (len(c.members), c.similarity), reverse=True)
    return clusters
