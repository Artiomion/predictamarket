"""
FinBERT sentiment analysis service.

Loads ProsusAI/finbert once on first call (lazy singleton, thread-safe).
All inference runs in a thread pool to avoid blocking the event loop.

Also exposes an embedding path: [CLS] hidden state from the base encoder,
projected through a pre-trained IncrementalPCA (32 components) to produce
the `sent_0..sent_31` features the TFT model was trained on.
"""

import asyncio
import os
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import structlog
import torch
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

logger = structlog.get_logger()

MODEL_NAME = "ProsusAI/finbert"
LABELS = ["positive", "negative", "neutral"]

# Path to PCA pickle — same artifact the TFT was trained with.
_MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
_PCA_PATH = _MODELS_DIR / "pca_model.pkl"
_N_PCA_COMPONENTS = 32


@dataclass
class SentimentResult:
    label: str          # positive | negative | neutral
    score: float        # confidence 0.0-1.0
    scores: dict[str, float]  # all three scores


class FinBERTSentiment:
    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None           # sequence-classification head
        self._base_model = None       # encoder (no head) — for [CLS] embeddings
        self._pca = None
        self._loaded = False
        self._embed_loaded = False
        self._lock = threading.Lock()

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self._model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            self._model.eval()
            self._loaded = True
            structlog.get_logger().info("finbert_loaded", model=MODEL_NAME)

    def _load_embed(self) -> None:
        """Load encoder + PCA for embedding path. Separate from classifier load."""
        with self._lock:
            if self._embed_loaded:
                return
            if self._tokenizer is None:
                self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self._base_model = AutoModel.from_pretrained(MODEL_NAME)
            self._base_model.eval()
            if _PCA_PATH.exists():
                with open(_PCA_PATH, "rb") as f:
                    self._pca = pickle.load(f)
                structlog.get_logger().info(
                    "pca_loaded", components=getattr(self._pca, "n_components_", "?"),
                )
            else:
                structlog.get_logger().warning("pca_missing", path=str(_PCA_PATH))
            self._embed_loaded = True

    def _predict_sync(self, text: str) -> SentimentResult:
        self._load()
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512, padding=True
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
        scores = {label: round(float(probs[i]), 4) for i, label in enumerate(LABELS)}
        best_idx = probs.argmax().item()
        return SentimentResult(
            label=LABELS[best_idx],
            score=round(float(probs[best_idx]), 4),
            scores=scores,
        )

    def _predict_batch_sync(self, texts: list[str]) -> list[SentimentResult]:
        self._load()
        if not texts:
            return []
        inputs = self._tokenizer(
            texts, return_tensors="pt", truncation=True, max_length=512,
            padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        results = []
        for i in range(len(texts)):
            scores = {label: round(float(probs[i][j]), 4) for j, label in enumerate(LABELS)}
            best_idx = probs[i].argmax().item()
            results.append(SentimentResult(
                label=LABELS[best_idx],
                score=round(float(probs[i][best_idx]), 4),
                scores=scores,
            ))
        return results

    async def predict(self, text: str) -> SentimentResult:
        return await asyncio.to_thread(self._predict_sync, text)

    async def predict_batch(self, texts: list[str], batch_size: int = 32) -> list[SentimentResult]:
        """Process texts in batches to manage memory. FIX #9: batch_size 16→32."""
        all_results: list[SentimentResult] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results = await asyncio.to_thread(self._predict_batch_sync, batch)
            all_results.extend(results)
        return all_results

    def _embed_batch_sync(self, texts: list[str]) -> np.ndarray:
        """Extract [CLS] hidden state then project to 32d via PCA.

        Returns: array shape (len(texts), 32). If PCA not available, returns
        shape (len(texts), 768) raw embeddings — caller can decide.
        """
        self._load_embed()
        if not texts:
            return np.zeros((0, _N_PCA_COMPONENTS), dtype=np.float32)

        inputs = self._tokenizer(
            texts, return_tensors="pt", truncation=True, max_length=512, padding=True,
        )
        with torch.no_grad():
            outputs = self._base_model(**inputs)
            cls = outputs.last_hidden_state[:, 0, :].cpu().numpy()  # (B, 768)

        if self._pca is None:
            return cls

        # IncrementalPCA.transform expects 2D array (samples, features)
        reduced = self._pca.transform(cls)
        return reduced.astype(np.float32)

    async def embed_batch(
        self, texts: list[str], batch_size: int = 16,
    ) -> np.ndarray:
        """Async wrapper — returns PCA vectors shape (N, 32)."""
        all_chunks: list[np.ndarray] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vecs = await asyncio.to_thread(self._embed_batch_sync, batch)
            all_chunks.append(vecs)
        if not all_chunks:
            return np.zeros((0, _N_PCA_COMPONENTS), dtype=np.float32)
        return np.vstack(all_chunks)


# Singleton
finbert = FinBERTSentiment()
