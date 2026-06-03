"""Walk a directory, read supported files, and run clustering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cluster import DEFAULT_SEED, Cluster, Document, cluster_documents
from .normalize import normalize

# Extensions handled in v0.1. PDF/DOCX land in v0.3.
TEXT_EXTS = {".txt", ".md", ".markdown", ".rst"}
HTML_EXTS = {".html", ".htm"}
SUPPORTED = TEXT_EXTS | HTML_EXTS


@dataclass
class ScanResult:
    total_files: int
    clusters: list[Cluster]
    all_paths: list[str]

    @property
    def redundant_count(self) -> int:
        # Every cluster of size n contributes (n - 1) redundant files.
        return sum(len(c.members) - 1 for c in self.clusters)

    @property
    def unique_count(self) -> int:
        return self.total_files - self.redundant_count

    def keep_list(self) -> list[str]:
        """Paths to keep: every scanned file minus the redundant members of
        each cluster. The first (sorted) member of each cluster is kept."""
        drop: set[str] = set()
        for c in self.clusters:
            drop.update(c.members[1:])
        return sorted(p for p in self.all_paths if p not in drop)


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            yield path


def scan(
    root: str | Path,
    *,
    k: int = 5,
    threshold: float = 0.85,
    num_perm: int = 128,
    seed: int = DEFAULT_SEED,
) -> ScanResult:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(root)

    docs: list[Document] = []
    for path in _iter_files(root):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        is_html = path.suffix.lower() in HTML_EXTS
        docs.append(Document(path=str(path), text=normalize(raw, is_html=is_html)))

    clusters = cluster_documents(
        docs, k=k, threshold=threshold, num_perm=num_perm, seed=seed
    )
    return ScanResult(
        total_files=len(docs),
        clusters=clusters,
        all_paths=[d.path for d in docs],
    )
