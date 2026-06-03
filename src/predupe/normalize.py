"""Text normalization and shingling.

The goal here is cheap, deterministic preprocessing: turn a raw document into a
set of shingles (overlapping word n-grams) that MinHash can fingerprint. We
deliberately discard formatting so that two files differing only in markup or
whitespace collapse to the same shingle set.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_WS = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    """Pull visible text out of HTML, skipping script/style content."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(self._chunks)


def strip_html(text: str) -> str:
    parser = _TextExtractor()
    parser.feed(text)
    return parser.text()


def normalize(text: str, *, is_html: bool = False) -> str:
    """Lowercase, strip markup, collapse whitespace.

    Returns a single clean string. Deterministic for a given input.
    """
    if is_html:
        text = strip_html(text)
    text = text.lower()
    text = _WS.sub(" ", text)
    return text.strip()


def shingles(text: str, k: int = 5) -> set[str]:
    """Return the set of k-word shingles for a normalized string.

    k controls sensitivity: smaller k catches shorter shared passages but
    raises false positives; larger k is stricter. Default 5 is a reasonable
    balance for prose.
    """
    words = text.split()
    if len(words) < k:
        # Document too short to shingle; treat the whole thing as one shingle
        # so it can still match identical short files.
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}
