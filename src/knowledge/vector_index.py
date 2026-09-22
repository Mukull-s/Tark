"""Deterministic in-process vector index over the authoritative knowledge corpus.

This module provides a real, verifiable **vector storage + retrieval** capability
for GraphRAG-style grounding: every policy rule, fraud typology, and regulatory
statute chunk is embedded into a fixed-dimension vector and retrieved by cosine
similarity against an investigation query derived from observed evidence.

Design notes (honest capability statement):
- The embedding is a deterministic hashing (feature-hashing) bag-of-words vector.
  It is reproducible, dependency-free, and auditable — no remote model required.
- The index is portable: the same vectors can be persisted as TigerGraph vector
  attributes on a ``Document`` vertex and queried with a vector-search GSQL
  function. This module is the deterministic, offline-executable realization of
  that retrieval contract; it does **not** claim live TigerGraph vector search
  unless a TigerGraph vector index is configured.
"""

import math
import hashlib
import re
from typing import List, Dict, Tuple, Optional

from src.knowledge.models import KnowledgeChunk
from src.knowledge.store import InvestigationKnowledgeBase

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class HashingVectorIndex:
    """Feature-hashing vector index with cosine-similarity retrieval."""

    def __init__(self, dim: int = 384):
        self.dim = max(64, int(dim))
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._vectors: Dict[str, List[float]] = {}

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for token in _tokenize(text):
            digest = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = digest % self.dim
            sign = 1.0 if (digest >> 7) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        searchable = " ".join([
            chunk.title or "",
            chunk.text or "",
            " ".join(chunk.applicable_rules or []),
            " ".join(chunk.applicable_typologies or []),
            chunk.governing_body or "",
        ])
        self._chunks[chunk.chunk_id] = chunk
        self._vectors[chunk.chunk_id] = self._embed(searchable)

    def build(self, chunks: List[KnowledgeChunk]) -> "HashingVectorIndex":
        for chunk in chunks:
            self.add_chunk(chunk)
        return self

    def search(self, query: str, top_k: int = 4) -> List[Tuple[str, float]]:
        if not self._vectors:
            return []
        q = self._embed(query)
        scored = []
        for cid, vec in self._vectors.items():
            sim = sum(a * b for a, b in zip(q, vec))
            scored.append((cid, sim))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:max(1, top_k)]

    def get_chunk(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        return self._chunks.get(chunk_id)

    def size(self) -> int:
        return len(self._chunks)


_DEFAULT_INDEX: Optional[HashingVectorIndex] = None


def get_default_vector_index(kb: Optional[InvestigationKnowledgeBase] = None) -> HashingVectorIndex:
    """Returns a process-wide, lazily-built vector index over the knowledge base."""
    global _DEFAULT_INDEX
    if _DEFAULT_INDEX is None:
        base = kb or InvestigationKnowledgeBase()
        _DEFAULT_INDEX = HashingVectorIndex().build(base.all_chunks())
    return _DEFAULT_INDEX
