"""
FinBERT sentiment analysis service.

Loads ProsusAI/finbert once on first call (lazy singleton, thread-safe).
All inference runs in a thread pool to avoid blocking the event loop.
"""

import asyncio
import threading
from dataclasses import dataclass

import structlog
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = structlog.get_logger()

MODEL_NAME = "ProsusAI/finbert"
LABELS = ["positive", "negative", "neutral"]


@dataclass
class SentimentResult:
    label: str          # positive | negative | neutral
    score: float        # confidence 0.0-1.0
    scores: dict[str, float]  # all three scores


class FinBERTSentiment:
    def __init__(self) -> None:
        self._tokenizer = None
        self._model = None
        self._loaded = False
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


# Singleton
finbert = FinBERTSentiment()
