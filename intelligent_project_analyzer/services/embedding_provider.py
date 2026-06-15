"""Embedding model loader with a deterministic local fallback."""

from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Union

from loguru import logger


class HashEmbeddingModel:
    """Small deterministic embedding fallback for local demos and tests.

    It is not a semantic model. It exists so the knowledge-base demo can be
    initialized without network access or writable HuggingFace cache.
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.is_fallback = True

    def encode(
        self,
        sentences: Union[str, Sequence[str]],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        single = isinstance(sentences, str)
        texts = [sentences] if single else list(sentences)
        vectors = [self._encode_one(text, normalize_embeddings=normalize_embeddings) for text in texts]
        return vectors[0] if single else vectors

    def _encode_one(self, text: str, normalize_embeddings: bool = True) -> List[float]:
        vector = [0.0] * self.dim
        tokens = self._tokens(text)
        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        if normalize_embeddings:
            norm = math.sqrt(sum(value * value for value in vector))
            if norm > 0:
                vector = [value / norm for value in vector]
        return vector

    @staticmethod
    def _tokens(text: str) -> List[str]:
        text = (text or "").lower()
        latin = re.findall(r"[a-z0-9_]+", text)
        cjk = re.findall(r"[\u4e00-\u9fff]", text)
        bigrams = [text[i : i + 2] for i in range(max(0, len(text) - 1)) if re.search(r"[\u4e00-\u9fff]", text[i : i + 2])]
        return latin + cjk + bigrams or [text[:32] or "empty"]


def load_embedding_model(model_name: str, dim: int = 1024):
    if _should_use_hash_fallback(model_name):
        logger.warning(f"Embedding model '{model_name}' has no usable local cache, using HashEmbeddingModel fallback")
        return HashEmbeddingModel(dim=dim)
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)
    except Exception as exc:
        logger.warning(f"Embedding model '{model_name}' unavailable, using HashEmbeddingModel fallback: {exc}")
        return HashEmbeddingModel(dim=dim)


def _should_use_hash_fallback(model_name: str) -> bool:
    if os.getenv("KNOWLEDGE_FORCE_HASH_EMBEDDING", "").lower() in {"1", "true", "yes"}:
        return True
    if os.getenv("KNOWLEDGE_ALLOW_MODEL_DOWNLOAD", "").lower() in {"1", "true", "yes"}:
        return False
    if Path(model_name).exists():
        return False

    cache_home = Path(os.getenv("HF_HOME") or ".cache/huggingface")
    model_cache_name = f"models--{model_name.replace('/', '--')}"
    snapshot_root = cache_home / "hub" / model_cache_name / "snapshots"
    if not snapshot_root.exists():
        return True
    return not any(snapshot.glob("config.json") for snapshot in snapshot_root.iterdir() if snapshot.is_dir())
