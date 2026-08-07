"""
Embeddings for codebase memory.

Two backends, chosen automatically:

  1. **Provider embeddings** (OpenAI-compatible `/embeddings`, incl. Voyage,
     Azure, or a local vLLM/Ollama endpoint) when a key is configured.
  2. **Hashed lexical vectors** otherwise — a deterministic bag-of-tokens
     projection into a fixed-dimension unit vector.

The fallback is not a placeholder: for code retrieval, identifier overlap is a
strong signal, and it means memory works on a laptop, in CI, and inside an
air-gapped self-hosted install with no embedding vendor at all. It is clearly
weaker than a trained embedding model on natural-language queries, which is why
the provider path is preferred whenever a key exists.

Vectors are stored as JSONB float arrays rather than requiring pgvector, so the
platform installs on stock Postgres 15 and on managed providers that don't offer
the extension. Swap in pgvector by changing `memory_service.retrieve()` only.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re

import httpx

from app.config import settings

log = logging.getLogger(__name__)

HASH_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def backend() -> str:
    if settings.embedding_api_key or settings.openai_api_key:
        return "provider"
    return "hashed"


def model_name() -> str:
    return settings.embedding_model if backend() == "provider" else f"hashed-lexical-{HASH_DIM}"


def embed(text: str) -> list[float]:
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if backend() == "provider":
        try:
            return _provider_embed(texts)
        except Exception:
            log.exception("Embedding provider failed — falling back to hashed vectors")
    return [_hashed_embed(t) for t in texts]


# ── Provider ──────────────────────────────────────────────────────────────────

def _provider_embed(texts: list[str]) -> list[list[float]]:
    key = settings.embedding_api_key or settings.openai_api_key
    base = (settings.embedding_base_url or settings.openai_base_url).rstrip("/")
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{base}/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": settings.embedding_model, "input": texts},
        )
    r.raise_for_status()
    rows = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
    return [_normalise(row["embedding"]) for row in rows]


# ── Hashed lexical fallback ───────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower())[:4000]:
        out.append(raw)
        # split snake_case and camelCase so `getUserToken` matches `user` + `token`
        if "_" in raw:
            out.extend(p for p in raw.split("_") if len(p) > 1)
        else:
            parts = re.findall(r"[a-z]+|\d+", raw)
            if len(parts) > 1:
                out.extend(p for p in parts if len(p) > 1)
    return out


def _hashed_embed(text: str) -> list[float]:
    vec = [0.0] * HASH_DIM
    for token in _tokenize(text):
        h = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")
        idx = h % HASH_DIM
        sign = 1.0 if (h >> 63) & 1 else -1.0
        vec[idx] += sign
    return _normalise(vec)


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


# ── Similarity ────────────────────────────────────────────────────────────────

def cosine(a: list[float], b: list[float]) -> float:
    """Both sides are stored normalised, so this is a dot product in practice."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n])) or 1.0
    nb = math.sqrt(sum(x * x for x in b[:n])) or 1.0
    return dot / (na * nb)
