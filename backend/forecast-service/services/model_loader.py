"""
TFT model loader — lazy singleton.
Loads checkpoint, config, dataset_params, PCA model, valid tickers.
"""

import hashlib
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


# Explicit checkpoint assignments — DO NOT rely on alphabetical sort.
# Selection based on walk-forward-lite ensemble study (see docs/model-eval.md):
#   ep5 = primary (best Top-20 Sharpe 1.36, solid MAPE 4.86%)
#   ep2 = ensemble member (best ConfLong Sharpe 5.70, WR 61.1%)
#   ep4 = ensemble member (best MAPE 1d 4.74%)
PRIMARY_CKPT = "tft-epoch=05-val_loss=9.3008.ckpt"
ENSEMBLE_CKPTS = [
    "tft-epoch=02-val_loss=8.8051.ckpt",
    "tft-epoch=04-val_loss=9.2586.ckpt",
    "tft-epoch=05-val_loss=9.3008.ckpt",
]

# SHA256 of exact weights we validated in the ensemble study.
# Mismatch logs a warning; we still load (useful for dev/retraining) but the
# warning is a canary for "somebody silently swapped the file" incidents.
CKPT_SHA256 = {
    "tft-epoch=02-val_loss=8.8051.ckpt": "55eeafea8fc92e1c44e4bee9cf7ac0fe431bcdf0cb8a35b2c62ae93a8e5cb126",
    "tft-epoch=04-val_loss=9.2586.ckpt": "b9ea9c7e6098a8745c9eb3252e9aa2bd14b8ccb8c53fa350fb924fbbcf95010f",
    "tft-epoch=05-val_loss=9.3008.ckpt": "ae103556b1fb1f5fbf5fd10c27b935b2e4f691bc0d5bc0afe0c6741e51d7330f",
}


def _verify_ckpt_sha(ckpt_path: str) -> None:
    name = os.path.basename(ckpt_path)
    expected = CKPT_SHA256.get(name)
    if expected is None:
        return  # unknown ckpt — skip (dev or retraining)
    h = hashlib.sha256()
    with open(ckpt_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        structlog.get_logger().warning(
            "ckpt_sha_mismatch", ckpt=name, expected=expected, actual=actual,
        )
    else:
        structlog.get_logger().info("ckpt_sha_verified", ckpt=name)


def _load_ckpt(ckpt_path: str):
    """Load a TFT checkpoint on CPU, with weights_only fallback for older lightning."""
    _verify_ckpt_sha(ckpt_path)
    from pytorch_forecasting import TemporalFusionTransformer
    try:
        m = TemporalFusionTransformer.load_from_checkpoint(
            ckpt_path, map_location="cpu", weights_only=False
        )
    except TypeError:
        m = TemporalFusionTransformer.load_from_checkpoint(
            ckpt_path, map_location="cpu"
        )
    m.eval()
    return m


class ModelArtifacts:
    """Thread-safe lazy loader for all TFT model artifacts.

    Primary model (ep5) loads eagerly on first use.
    Ensemble members (ep2, ep4) load on first ensemble request.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ensemble_lock = threading.Lock()
        self._loaded = False
        self._ensemble_loaded = False
        self.config: dict = {}
        self.dataset_params: dict = {}
        self.tft_model = None
        self.ensemble_models: list = []  # [ep2, ep4, ep5] in order
        self.pca = None
        self.finbert_tokenizer = None
        self.finbert_model = None
        self.valid_tickers: set[str] = set()
        self.blocklisted_tickers: set[str] = set()
        self.known_tickers: list[str] = []
        self.device = "cpu"
        self.checkpoint_name: str = ""

    def _load_sync(self) -> None:
        """Load primary artifacts. Runs in a thread."""
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

            # 3. Valid tickers (346 S&P 500 ∩ trained) minus the blocklist.
            # Blocklist = tickers where model predictions are unreliable due to
            # post-split / corporate-action data mismatch between training data
            # (raw HuggingFace prices pre-split) and live data (yfinance
            # post-split). These produce MAPE >> 10% and catastrophically wrong
            # rank positions — better to return 404 than mislead the user. Will
            # be re-enabled after a retrain on split-adjusted prices.
            ticker_file = models_dir / "old_model_sp500_tickers.txt"
            all_tickers = {
                t.strip().upper()
                for t in ticker_file.read_text().strip().splitlines()
                if t.strip()
            }
            blocklist_file = models_dir / "blocklist_tickers.txt"
            blocklist: set[str] = set()
            if blocklist_file.exists():
                blocklist = {
                    t.strip().upper()
                    for t in blocklist_file.read_text().strip().splitlines()
                    if t.strip() and not t.strip().startswith("#")
                }
            self.valid_tickers = all_tickers - blocklist
            self.blocklisted_tickers = blocklist
            if blocklist:
                structlog.get_logger().info(
                    "blocklist_applied",
                    n_blocklisted=len(blocklist),
                    n_valid=len(self.valid_tickers),
                )

            # 4. Primary TFT checkpoint (ep5)
            self.checkpoint_name = PRIMARY_CKPT
            ckpt_path = str(models_dir / PRIMARY_CKPT)
            if not os.path.exists(ckpt_path):
                # Fallback: pick last available ckpt (legacy dev environments)
                ckpts = sorted([f for f in os.listdir(models_dir) if f.endswith(".ckpt")])
                if not ckpts:
                    raise FileNotFoundError("No .ckpt file found in models dir")
                self.checkpoint_name = ckpts[-1]
                ckpt_path = str(models_dir / self.checkpoint_name)
                structlog.get_logger().warning(
                    "primary_ckpt_missing_using_fallback",
                    expected=PRIMARY_CKPT, using=self.checkpoint_name,
                )

            self.tft_model = _load_ckpt(ckpt_path)

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
            structlog.get_logger().info(
                "models_loaded",
                tft_ckpt=self.checkpoint_name,
                valid_tickers=len(self.valid_tickers),
            )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_sync()

    def ensure_ensemble_loaded(self) -> None:
        """Lazy-load the 3 ensemble checkpoints (ep2, ep4, ep5).
        ep5 is the primary and may already be loaded — reuse it to save RAM.
        """
        self.ensure_loaded()
        with self._ensemble_lock:
            if self._ensemble_loaded:
                return

            models_dir = _MODELS_DIR
            structlog.get_logger().info("loading_ensemble", ckpts=ENSEMBLE_CKPTS)

            ensemble = []
            for ckpt_name in ENSEMBLE_CKPTS:
                if ckpt_name == self.checkpoint_name and self.tft_model is not None:
                    # Reuse already-loaded primary
                    ensemble.append(self.tft_model)
                    continue
                ckpt_path = str(models_dir / ckpt_name)
                if not os.path.exists(ckpt_path):
                    structlog.get_logger().error("ensemble_ckpt_missing", ckpt=ckpt_name)
                    raise FileNotFoundError(f"Ensemble checkpoint missing: {ckpt_name}")
                ensemble.append(_load_ckpt(ckpt_path))

            self.ensemble_models = ensemble
            self._ensemble_loaded = True
            structlog.get_logger().info("ensemble_loaded", count=len(ensemble))

    @property
    def is_ensemble_loaded(self) -> bool:
        return self._ensemble_loaded


# Singleton
artifacts = ModelArtifacts()
