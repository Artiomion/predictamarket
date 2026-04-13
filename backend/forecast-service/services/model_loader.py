"""
TFT model loader — lazy singleton.
Loads checkpoint, config, dataset_params, PCA model, valid tickers.
"""

import json
import os
import pickle
import threading
from pathlib import Path

import structlog
import torch

# Monkeypatch torchmetrics: CUDA-trained checkpoints fail on CPU-only machines
# during both load_from_checkpoint AND predict() because torchmetrics._apply
# tries to create tensors on the original CUDA device. Must be applied at import
# time, before any model loading.
try:
    import torchmetrics
    _orig_metric_apply = torchmetrics.Metric._apply
    def _safe_metric_apply(self_metric, fn, *args, **kwargs):
        try:
            return _orig_metric_apply(self_metric, fn, *args, **kwargs)
        except AssertionError:
            return self_metric
    torchmetrics.Metric._apply = _safe_metric_apply
except ImportError:
    pass

logger = structlog.get_logger()

# Model artifacts directory — in Docker: /models, locally: project_root/models
_MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).resolve().parent.parent.parent.parent / "models"))


class ModelArtifacts:
    """Thread-safe lazy loader for all TFT model artifacts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self.config: dict = {}
        self.dataset_params: dict = {}
        self.tft_model = None
        self.pca = None
        self.finbert_tokenizer = None
        self.finbert_model = None
        self.valid_tickers: set[str] = set()
        self.known_tickers: list[str] = []
        self.device = "cpu"
        self.checkpoint_name: str = ""

    def _load_sync(self) -> None:
        """Load all artifacts. Runs in a thread."""
        with self._lock:
            if self._loaded:
                return

            torch.set_float32_matmul_precision("medium")
            # Force CUDA-trained checkpoints to load on CPU
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = ""

            models_dir = _MODELS_DIR
            structlog.get_logger().info("loading_models", dir=str(models_dir))

            # 1. Config
            with open(models_dir / "config.json") as f:
                self.config = json.load(f)

            # 2. Dataset params (requires pytorch_forecasting)
            with open(models_dir / "training_dataset_params.pkl", "rb") as f:
                self.dataset_params = pickle.load(f)

            self.known_tickers = list(
                self.dataset_params["categorical_encoders"]["__group_id__ticker"].classes_.keys()
            )

            # 3. Valid tickers (94 S&P 500)
            ticker_file = models_dir / "old_model_sp500_tickers.txt"
            self.valid_tickers = {
                t.strip().upper()
                for t in ticker_file.read_text().strip().splitlines()
                if t.strip()
            }

            # 4. TFT checkpoint
            ckpts = sorted([f for f in os.listdir(models_dir) if f.endswith(".ckpt")])
            if not ckpts:
                raise FileNotFoundError("No .ckpt file found in models dir")

            from pytorch_forecasting import TemporalFusionTransformer

            self.checkpoint_name = ckpts[-1]
            ckpt_path = str(models_dir / self.checkpoint_name)
            try:
                self.tft_model = TemporalFusionTransformer.load_from_checkpoint(
                    ckpt_path, map_location="cpu", weights_only=False
                )
            except TypeError:
                # Older lightning doesn't support weights_only kwarg
                self.tft_model = TemporalFusionTransformer.load_from_checkpoint(
                    ckpt_path, map_location="cpu"
                )
            self.tft_model.eval()

            # 5. PCA model
            with open(models_dir / "pca_model.pkl", "rb") as f:
                self.pca = pickle.load(f)

            # 6. FinBERT (for live news sentiment — optional, may not be cached)
            try:
                from transformers import AutoModel, AutoTokenizer
                self.finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                self.finbert_model = AutoModel.from_pretrained("ProsusAI/finbert")
                self.finbert_model.eval()
            except Exception:
                structlog.get_logger().warning("finbert_not_available", reason="model not cached, sentiment from DB only")
                self.finbert_tokenizer = None
                self.finbert_model = None

            self._loaded = True
            structlog.get_logger().info("models_loaded", tft_ckpt=ckpts[-1], valid_tickers=len(self.valid_tickers))

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_sync()


# Singleton
artifacts = ModelArtifacts()
