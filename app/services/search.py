"""Knowledge-base retrieval: BM25 keyword search (works for Georgian, English, Russian with no
external services) plus an optional embedding similarity boost."""

from __future__ import annotations

import math
import re
import threading
from collections import Counter, OrderedDict
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Chunk, Document, Workspace
from app.services import embeddings

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_PREFIX = 5  # crude stemming: "მიწოდება"/"მიწოდების" or "delivery"/"deliveries" share a prefix token

STOPWORDS = {
    # en
    "the", "a", "an", "is", "are", "was", "be", "to", "of", "and", "or", "in", "on", "for", "with",
    "do", "does", "you", "your", "i", "me", "my", "we", "it", "this", "that", "can", "how", "what",
    # ka
    "და", "რომ", "არის", "ეს", "ის", "თუ", "ან", "მაგრამ", "კი", "არ", "მე", "თქვენ", "ჩვენ",
    "რა", "როგორ", "რომელიც", "უნდა", "შეიძლება", "თქვენი", "ჩემი", "ხართ", "გაქვთ", "მაქვს",
    # ru
    "и", "в", "во", "на", "с", "со", "что", "как", "это", "у", "вы", "мы", "я", "ли", "не", "а",
    "по", "для", "вас", "есть", "ваш", "можно",
}


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if tok in STOPWORDS or (len(tok) < 2 and not tok.isdigit()):
            continue
        tokens.append(tok)
        if len(tok) > _PREFIX + 1 and not tok.isdigit():
            tokens.append(tok[:_PREFIX] + "*")
    return tokens


@dataclass
class Hit:
    chunk_id: int
    document_id: int
    title: str
    kind: str
    source: str
    content: str
    score: float
    coverage: float  # share of distinct query words found in this chunk (0..1)


@dataclass(frozen=True)
class _Row:
    chunk_id: int
    document_id: int
    title: str
    kind: str
    source: str
    content: str
    embedding: bytes | None


class _Index:
    def __init__(self, rows: list[_Row]) -> None:
        self.rows = rows
        self.docs = [Counter(tokenize(f"{row.title}\n{row.content}")) for row in rows]
        self.lengths = [sum(c.values()) for c in self.docs]
        self.avgdl = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        df: Counter[str] = Counter()
        for c in self.docs:
            df.update(c.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        vectors = [embeddings.from_bytes(row.embedding) for row in rows if row.embedding]
        self.matrix: np.ndarray | None = None
        if rows and len(vectors) == len(rows) and len({v.shape for v in vectors}) == 1:
            m = np.vstack(vectors)
            norms = np.linalg.norm(m, axis=1, keepdims=True)
            self.matrix = m / np.where(norms == 0, 1, norms)

    def bm25(self, query_tokens: list[str], k1: float = 1.4, b: float = 0.75) -> list[float]:
        scores = [0.0] * len(self.docs)
        terms = set(query_tokens)
        for i, counts in enumerate(self.docs):
            dl = self.lengths[i] or 1
            s = 0.0
            for t in terms:
                f = counts.get(t)
                if f:
                    s += self.idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / (self.avgdl or 1)))
            scores[i] = s
        return scores


_cache: OrderedDict[int, tuple[int, _Index]] = OrderedDict()
_lock = threading.Lock()
_MAX_CACHED = 300


def invalidate(workspace_id: int) -> None:
    with _lock:
        _cache.pop(workspace_id, None)


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _get_index(db: Session, ws: Workspace) -> _Index:
    with _lock:
        cached = _cache.get(ws.id)
        if cached and cached[0] == ws.kb_version:
            _cache.move_to_end(ws.id)
            return cached[1]
    rows = [
        _Row(*r)
        for r in db.execute(
            select(
                Chunk.id, Document.id, Document.title, Document.kind, Document.source,
                Chunk.content, Chunk.embedding,
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.workspace_id == ws.id)
            .order_by(Chunk.id)
        )
    ]
    index = _Index(rows)
    with _lock:
        _cache[ws.id] = (ws.kb_version, index)
        _cache.move_to_end(ws.id)
        while len(_cache) > _MAX_CACHED:
            _cache.popitem(last=False)
    return index


def search(db: Session, ws: Workspace, query: str, settings: Settings, k: int = 5) -> list[Hit]:
    index = _get_index(db, ws)
    if not index.rows:
        return []
    q_tokens = tokenize(query)
    scores = index.bm25(q_tokens)
    top = max(scores) if scores else 0.0
    combined = [s / top if top > 0 else 0.0 for s in scores]

    if index.matrix is not None and embeddings.enabled(settings):
        vec = embeddings.embed_safely([query], settings)
        if vec:
            q = np.asarray(vec[0], dtype=np.float32)
            if q.shape[0] == index.matrix.shape[1]:
                q = q / (np.linalg.norm(q) or 1.0)
                sims = index.matrix @ q
                combined = [0.5 * c + 0.5 * max(0.0, float(s)) for c, s in zip(combined, sims)]

    words = {t for t in q_tokens if not t.endswith("*")}
    order = sorted(range(len(combined)), key=lambda i: combined[i], reverse=True)[:k]
    hits: list[Hit] = []
    for i in order:
        if combined[i] <= 0.05:
            continue
        row = index.rows[i]
        counts = index.docs[i]
        found = sum(1 for w in words if w in counts or (len(w) > _PREFIX + 1 and w[:_PREFIX] + "*" in counts))
        hits.append(
            Hit(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                title=row.title,
                kind=row.kind,
                source=row.source,
                content=row.content,
                score=round(combined[i], 4),
                coverage=(found / len(words)) if words else 0.0,
            )
        )
    return hits
