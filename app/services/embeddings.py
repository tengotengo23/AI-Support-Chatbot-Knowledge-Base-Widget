"""Optional vector embeddings (OpenAI-compatible or Ollama). Keyword search works without them."""

from __future__ import annotations

import logging

import httpx
import numpy as np

from app.config import Settings

log = logging.getLogger(__name__)

DEFAULT_MODELS = {"openai": "text-embedding-3-small", "ollama": "nomic-embed-text"}


def enabled(settings: Settings) -> bool:
    return settings.embeddings_provider in DEFAULT_MODELS


def _model(settings: Settings) -> str:
    return settings.embeddings_model or DEFAULT_MODELS[settings.embeddings_provider]


def embed(texts: list[str], settings: Settings) -> list[list[float]]:
    if not texts:
        return []
    out: list[list[float]] = []
    for start in range(0, len(texts), 64):
        batch = texts[start : start + 64]
        if settings.embeddings_provider == "openai":
            resp = httpx.post(
                f"{settings.openai_base_url}/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": _model(settings), "input": batch},
                timeout=60,
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
        elif settings.embeddings_provider == "ollama":
            resp = httpx.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": _model(settings), "input": batch},
                timeout=120,
            )
            resp.raise_for_status()
            out.extend(resp.json()["embeddings"])
        else:
            raise ValueError("Embeddings are disabled")
    return out


def embed_safely(texts: list[str], settings: Settings) -> list[list[float]] | None:
    """Embeddings are an optional boost: on any failure we log and fall back to keyword search."""
    if not enabled(settings) or not texts:
        return None
    try:
        return embed(texts, settings)
    except Exception as exc:  # noqa: BLE001
        log.warning("embedding failed, using keyword search only: %s", exc)
        return None


def to_bytes(vector: list[float]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_bytes(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)
