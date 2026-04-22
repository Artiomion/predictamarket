# ML Model Documentation

Full documentation of the Temporal Fusion Transformer (TFT) that powers
PredictaMarket's forecasts. Covers architecture, training, test results,
ensemble construction, and the "radical honesty" policy for publishing
metrics.

**Audience:** ML engineers, quant researchers, institutional evaluators,
anyone auditing our claims.

---

## 1. TL;DR

- **Architecture:** Temporal Fusion Transformer (Google), 16.3M parameters,
  via `pytorch-forecasting` 1.1.1.
- **Training universe:** 400 tickers (347 S&P 500 + 53 historical / mid-cap
  for data diversity), ~2.4M rows of history from 2000-03-14 through
  2026-04-02.
- **Input:** 107 features (price, technicals, macro, SEC financials,
  FinBERT sentiment PCA, calendar).
- **Output:** 7 quantiles × 22 trading days = full distributional forecast
  for the next ~1 month.
- **Production ensembles:** 3 checkpoints (ep2 + ep4 + ep5) used in two
  different weight configurations depending on the use case:
  - **ep5-heavy** `[0.2, 0.3, 0.5]` — Top Picks + per-ticker ranking
    (maximises Top-20 Sharpe: 1.49 back-test vs 1.45 equal-weight)
  - **ep2-heavy** `[0.5, 0.3, 0.2]` — Alpha Signals consensus filter
    (maximises Consensus WR: 64.3% back-test vs 63% equal-weight)
- **Universe in service:** 346 S&P 500 tickers (intersection of 400 trained
  ∩ current S&P 500).

### Metrics summary

| Metric                        | Back-test (raw) | Live target (what we publish) |
|-------------------------------|-----------------|-------------------------------|
| Top-20 Sharpe (ep5-heavy)     | 1.49            | **~1.0**                      |
| Top-20 Return (23 days)       | +19.74%         | — (back-test only)            |
| Consensus BUY Sharpe (ep2-heavy) | 8.04         | **~1.3**                      |
| Consensus BUY win rate (ep2-heavy) | 64.3% (N=28) | **~56%**                  |
| 1-day MAPE                    | 4.75%           | ~5–6%                         |
| 22-day MAPE                   | 12.63%          | ~14–16%                       |
| 1-day directional accuracy    | 48.1%           | **Not marketed** — coin flip  |
| 22-day directional accuracy   | 52.2%           | **Not marketed** — barely above random |
| Alpha vs S&P 500 (23 days)    | +12.01 pp       | **~+4 pp**                    |

Why the live targets are lower — see §8 "Shrinkage methodology".

---

## 2. Architecture

Temporal Fusion Transformer (TFT), originally from Google Research
([paper](https://arxiv.org/abs/1912.09363)). Implemented via
`pytorch-forecasting`, an opinionated wrapper around PyTorch Lightning.

| Hyperparameter          | Value                     |
|-------------------------|---------------------------|
| `hidden_size`           | 256                       |
| `attention_heads`       | 4                         |
| `hidden_continuous_size`| 128                       |
| `dropout`               | 0.1                       |
| Parameters              | 16.27M                    |
| Checkpoint size on disk | 197.6 MB (each)           |
| Encoder length          | **60** trading days (~3 months history) |
| Prediction length       | **22** trading days (~1 month forecast) |
| Output quantiles        | 7: [0.02, 0.10, 0.25, 0.50, 0.75, 0.90, 0.98] |
| Loss                    | QuantileLoss              |
| Target                  | `Close` (closing price)   |
| Normalizer              | `GroupNormalizer(groups=['ticker'], transformation='softplus')` |

### Why these choices

- **TFT over LSTM / Transformer**: TFT has built-in variable selection
  networks (VSN) which tell you which of the 107 features mattered for
  each prediction. We surface this as the "What Moved the Prediction"
  waterfall on the ticker page. Vanilla LSTM doesn't give you that.
- **Encoder 60 / predict 22**: matches common quant horizons — "3-month
  history predicts 1-month forward". Extending encoder beyond 60
  doubled training time without improving val-loss.
- **Softplus transformation**: prices are strictly positive; softplus
  (log(1+exp(x))) maps (-∞, ∞) → (0, ∞) smoothly. Per-ticker groups so
  the normalizer learns each stock's price scale independently.
- **7 quantiles**: gives you both 80% CI (q10–q90) and 95% CI (q02–q98)
  from a single forward pass. Median (q50) is the point estimate.

---

## 3. Training Data

### Dataset

Source: HuggingFace dataset
[`Wenyan0110/Multimodal-Dataset-Image_Text_Table_TimeSeries-for-Financial-Time-Series-Forecasting`](https://huggingface.co/datasets/Wenyan0110/Multimodal-Dataset-Image_Text_Table_TimeSeries-for-Financial-Time-Series-Forecasting).

Contains Time-Series CSV + News JSONL + SEC Financials tables for 2,638
tickers.

### Ticker selection

- **2,638** tickers in HuggingFace dataset.
- → filter to top 400 by data completeness → `old_model_400_tickers.txt`.
- → intersect with current S&P 500 constituents → **346** tickers used
  in production (`old_model_sp500_tickers.txt`).

The 54 non-S&P tickers in the 400 were kept during training to preserve
time-series diversity (former S&P members, foreign-listed, dual-class
shares with long history), but they're not in the service universe.

Notebook counted 347 S&P 500 ∩ 400 but shipping file has 346 — one ticker
was likely de-listed or renamed between snapshot and packaging.

### Train / Val / Test split

| Split | Window                         | Rows (actual) |
|-------|--------------------------------|---------------|
| Train | 2000-03-14 → 2025-06-30        | **2,444,801** |
| Val   | 2025-07-01 → 2025-10-31        | **34,800**    |
| Test  | 2025-11-01 → 2026-04-02        | **41,600**    |

The test set is further windowed into **9,200 sliding windows** (each one
a 60-day encoder + 22-day prediction frame) for evaluation of DirAcc /
MAPE.

### Sample weighting

Exponential decay with half-life = 504 trading days (~2 years). Rationale:
market regimes from 20 years ago matter less than those from 2 years ago,
but they still contribute signal.

---

## 4. Features (107 total)

Exact names from `config.json` → `time_varying_unknown_reals`:

| Category | Count | Examples |
|---|---|---|
| OHLCV | 5 | `Open`, `High`, `Low`, `Volume`, `Capital Gains` |
| Technical | 15 | `log_return`, `volatility_{5d,20d}`, `ma_{5,20,50}`, `rsi_14`, `volume_ma_20`, `price_to_ma{20,50}`, `momentum_{5d,20d}`, `pct_from_52wk_{high,low}`, `beta_spy_20d` |
| SEC Financials (XBRL) | 27 | `Assets`, `Liabilities`, `StockholdersEquity`, `NetCashProvidedByUsedIn{Operating,Investing,Financing}Activities`, `RetainedEarningsAccumulatedDeficit`, `PropertyPlantAndEquipmentNet`, `InventoryNet`, `AccountsPayableCurrent`, `AccountsReceivableNetCurrent`, `DividendsCommonStockCash`, … |
| FinBERT Sentiment PCA | 32 + `news_count` | `sent_0`..`sent_31` — 768-dim FinBERT [CLS] embeddings compressed via `IncrementalPCA(n=32)` |
| yfinance Macro | 8 | `vix`, `treasury_10y`, `sp500`, `dxy`, `gold`, `oil`, `vix_ma5`, `sp500_return` |
| FRED Macro | 7 | `cpi`, `unemployment`, `fed_funds_rate`, `yield_curve_spread`, `m2_money_supply`, `wti_crude`, `fred_vix` |
| Earnings | 5 | `eps_surprise_pct`, `earnings_beat`, `earnings_miss`, `has_earnings`, `days_since_earnings` |
| Insider | 3 | `insider_buys`, `insider_sells`, `insider_net` |
| Calendar / Events | 4 | `vix_contango`, `days_to_fomc`, `is_options_expiration`, `is_quad_witching` |
| **Categorical (static)** | — | `ticker`, `sector` |
| **Categorical (time-varying known)** | — | `day_of_week`, `month` |

### Important caveat: sentiment features are largely unused

The 32 FinBERT-PCA columns (`sent_0`..`sent_31`) do **not** appear in the
top-20 Variable Importance from the trained TFT. The model effectively
learns from OHLCV / technicals / SEC financials, not news.

Marketing copy says "107 data signals" which is literally true, but ~32
of them carry near-zero weight. For the next retrain we'll either:
- Drop them (simpler model, faster inference)
- Or up-weight news loss during training to force the model to use them.

---

## 5. Training Process

- **Hardware:** NVIDIA A100 40GB (Google Colab Pro)
- **Framework:** Lightning 2.x + pytorch-forecasting 1.1.1
- **Batch size:** 128
- **Learning rate:** 3e-4 initial, ReduceLROnPlateau (patience=4)
- **Gradient clip:** 0.1
- **Precision:** fp32 (fp16 broke softplus attention numerically)
- **`limit_train_batches`:** 0.5 (50% of batches per epoch for speed)
- **Workers:** 8 persistent
- **EarlyStopping:** patience=5, monitor=`val_loss`
- **`save_top_k`:** -1 (all epoch checkpoints kept)

### Training curve

7 epochs saved (ep0–ep6). Training stopped early around ep6 (val loss
plateau). Each epoch = ~2 hours on A100 → ~14 hours total, ~75 compute
units in Colab Pro.

### Val-loss confounder

The validation loss signal was noisy because `predict=True` builds
one window per ticker per epoch → only 400 validation samples. That's
insufficient for a stable val-loss trend. EarlyStopping triggered at a
plausibly-wrong epoch.

Real per-epoch performance was measured afterward on the 9,200-sample
test set with `predict=False`. That's where we pick the ensemble members
(see §6).

---

## 6. Ensemble Construction

Full per-epoch test performance (measured on N=9,200 sliding windows,
`predict=False`):

| Ep | Top-20 % | Top-20 Sh | ConfLong Sh | ConfLong N | ConfLong WR | MAPE 1d | DirAcc 22d |
|---:|--:|--:|--:|--:|--:|--:|--:|
| 0  | +10.13% | 0.70 | −4.21 |   5 | 40.0% | 5.37 | 0.498 |
| 1  |  +2.82% | 0.71 |  2.19 | 513 | 59.8% | 6.60 | 0.523 |
| **2** |  +4.44% | 0.97 | **5.70 ⭐** |  36 | 61.1% | 5.32 | 0.535 |
| 3  |  +2.71% | 0.65 |  0.76 |  99 | 48.5% | 5.19 | 0.517 |
| **4** | +13.87% | 0.94 |  3.67 |  57 | 57.9% | **4.74 ⭐** | 0.518 |
| **5** | **+17.77% ⭐** | **1.36 ⭐** |  3.02 |  57 | 57.9% | 4.86 | 0.512 |
| 6  |  +3.24% | 0.76 |  4.14 |  37 | 59.5% | 5.15 | 0.499 |

Three "best-of" selections:

- **ep5** → best Top-20 ranking single-model (Sharpe 1.36, return +17.77%)
- **ep2** → best Confident Long single-model (Sharpe 5.70, WR 61.1%)
- **ep4** → best short-horizon accuracy (MAPE 1d 4.74%)

### Weight search — three variants tested

The notebook tested 3 weight configurations on the same data:

| Weights           | Top-20 % | Top-20 Sharpe | ConfLong Sh | N  | ConfLong WR | MAPE 1d | DirAcc 22d |
|---|--:|--:|--:|--:|--:|--:|--:|
| Equal `[1/3,1/3,1/3]` | +19.19% | 1.45     | **8.15** 🥇 | 27 | 63.0%       | 4.78    | 0.527      |
| **ep5-heavy `[0.2,0.3,0.5]`** 🏆 | **+19.74%** 🥇 | **1.49** 🥇 | 2.01        | 35 | 54.3%       | 4.75    | 0.522      |
| **ep2-heavy `[0.5,0.3,0.2]`**    | +17.10% | 1.31          | 8.04        | 28 | **64.3%** 🥇 | 4.86    | 0.531      |

**There is no universal best ensemble** — each weight configuration
optimises a different metric.

### Production: two ensembles, one per surface

Different product surfaces care about different metrics:

- **Top Picks** (ranking product) → users care about Top-20 Sharpe.
  The more accurate the rank ordering, the better the basket of
  diversified picks performs.
- **Alpha Signals** (conviction filter) → users care about Win Rate.
  Each signal is a concentrated bet; they need most to work, not an
  average.
- **Per-ticker rank** (same value prop as Top Picks) → same optimiser.

```python
# services/ensemble.py — weights parameter drives behaviour

# Top Picks batch + per-ticker rank → ep5-heavy
q_ens = 0.2*q_ep2 + 0.3*q_ep4 + 0.5*q_ep5   # Sharpe 1.49 back-test

# Alpha Signals batch + Pro signal endpoint → ep2-heavy
q_ens = 0.5*q_ep2 + 0.3*q_ep4 + 0.2*q_ep5   # WR 64.3% back-test
```

Cost: 3× inference time and 3× memory vs single-model. Since ensemble
batch runs in Airflow (no user latency), this is acceptable. The live
"Refresh Forecast" path on the ticker page still uses ep5 single
(~10s) for UX reasons — next Airflow cron overwrites with the
ensemble result within the hour.

### Ensemble metrics shipped (vs best individual)

**Top Picks path (ep5-heavy):**

| Metric | Ensemble | vs ep5 alone |
|---|---|---|
| Top-20 Sharpe | 1.49 | +0.13 (+9.6%) |
| Top-20 Return | +19.74% | +1.97 pp |
| MAPE 1d | 4.75% | +0.11 pp (marginally better) |

**Alpha Signals path (ep2-heavy):**

| Metric | Ensemble | vs ep2 alone |
|---|---|---|
| ConfLong Sharpe | 8.04 | +2.34 |
| ConfLong Win Rate | 64.3% | +3.2 pp |
| ConfLong N trades | 28 | vs 36 (slightly more selective) |

### Ensemble caveats (the honest bit)

1. **Residual correlation between the 3 models is very high:**
   - `corr(ep2, ep4) = 0.978`
   - `corr(ep2, ep5) = 0.989`
   - `corr(ep4, ep5) = 0.989`

   At 0.98+, the diversification benefit is minimal. The 3 models are
   essentially the same model at 3 slightly different training stages.
   The training notebook's own verdict: *"MARGINAL — worth testing in
   live but not obvious win"*.

2. **Price-averaged, not majority-voted.** We tested majority-vote
   ("each model independently signals UP or DOWN, take majority"). It
   improved DirAcc by <1.5 pp which is inside the noise band (SE ≈
   0.52 pp at N=9200). Notebook verdict: *"NOT WORTH IT"*. So we stayed
   with the simpler price-averaging approach.

3. **Single-seed ensemble.** All 7 checkpoints come from the same
   training run (different epochs). Not 3 independent seeds. A proper
   ensemble would train 3 models with different random states — not done
   here due to compute cost.

---

## 7. Inference — Implementation Details

### Direct forward pass, not `.predict()`

**This is important.** Lightning's `model.predict()` applies the
`GroupNormalizer` inverse transform, which produces `NaN` on live data
from 2026 because the input distribution has drifted beyond what the
normalizer was fit to.

Fix: use raw forward pass.

```python
# services/inference.py
batch = next(iter(infer_dl))
x, _ = batch
with torch.no_grad():
    raw_output = tft_model(x)         # NOT tft_model.predict(...)
q = raw_output["prediction"][0].detach().cpu().numpy()  # (22, 7)
```

Without this, ~60% of live forecasts come back NaN.

### time_idx handling

`time_idx` must continue the sequence from training. We offset live data
so the first row in today's 60-day window has `time_idx = 6428 + i`
where 6428 is the trading-day count from 2000-03-14 to the first live
row. Using `range(0, N)` breaks the model (outside training range → NaN).

### Backfill + sanity check

Before inference, we call `_backfill_fresh_prices(ticker)`:

1. Fetch last 5 days from yfinance.
2. **Sanity check**: if the new close differs from the latest DB close by
   more than 50%, reject the backfill (without claiming the TTL slot)
   and log `backfill_rejected_extreme_delta`. Protects against
   rate-limit-induced stale data that once silently corrupted 33 tickers'
   current_close values with pre-split unadjusted prices.
3. Upsert into `market.price_history` if sanity-check passes.

The TTL cache is 5 min; rejections don't consume the slot so the next
request retries immediately.

### Live feature coverage vs training

| Source | Training | Live | Coverage |
|---|---|---|---|
| OHLCV | ✓ | ✓ (yfinance) | 100% |
| Technicals | ✓ | ✓ (computed) | 100% |
| Macro (yfinance) | ✓ | ✓ (cron every 15 min) | 100% |
| FRED macro | ✓ | ✓ (daily DAG) | 100% |
| Earnings (5 cols) | ✓ | ✓ (yfinance) | 100% |
| Insider (3 cols) | ✓ | ✓ (yfinance) | 100% |
| Calendar (4 cols) | ✓ | ✓ (hardcoded dates) | 100% |
| Sentiment (32 PCA) | ✓ | ✓ (FinBERT cron) | 100% |
| SEC Financials (27 cols) | ✓ | partial | ~50–90% depending on ticker |

The SEC financials coverage gap is real: XBRL tagging varies wildly by
company and filing. For AAPL / MSFT / NVDA we get ~90% of the 27
columns; for smaller tickers sometimes only 40–60%. Missing columns
default to 0 — model learned to handle that gracefully during training.

---

## 8. Live Targets — Shrinkage Methodology

**Core claim:** back-test numbers (Sharpe 1.49 ep5-heavy, Sharpe 8.04
ep2-heavy, 64.3% Consensus WR, 52.2% DirAcc 22d, +12.01 pp alpha)
will NOT repeat verbatim in live trading. Publishing them as-is would
be misleading. Note: 22-day DirAcc is already essentially coin-flip in
back-test, so we don't publish it at all — no live target, no caveat
tooltip, no mention as a strength.

### Factors that will degrade back-test performance

| Factor | Impact on Sharpe | Why |
|---|---|---|
| Small sample variance | 0.5–0.7× | 27 Consensus trades is too few for Sharpe to stabilise; 460 Top-20 positions is better but still 23-day window |
| Transaction costs | 0.7–0.85× | Slippage 0.02–0.1% per trade × hundreds of daily positions + commissions |
| Data-snooping bias | 0.75–0.85× | We picked the 3 best epochs out of 7; multiple testing inflates observed Sharpe |
| Overfitting | 0.60–0.80× | Especially acute for the Consensus filter — the 27 "winners" may be a lucky subset |
| Regime shift | 0.5–0.8× | Live disagreement score is **3.5× higher than training distribution** → current market is out-of-distribution |
| Survivorship bias | 0.85–0.95× | The 346 "current S&P 500" universe excludes companies that failed |

Multiplied together, the cumulative shrinkage factor is roughly
**0.25–0.45×** for the Consensus strategy and **0.55–0.75×** for Top-20.

Applied to current ep5-heavy / ep2-heavy back-test numbers:
- Top-20 Sharpe 1.49 (ep5-heavy) × 0.67 ≈ **1.0** (our live target)
- Consensus Sharpe 8.04 (ep2-heavy) × 0.16 ≈ **1.3** (live target)
- Consensus WR 64.3% (ep2-heavy) × 0.87 ≈ **56%** (live target)
- Alpha 12.01 pp × 0.33 ≈ **+4 pp**
- DirAcc 22d 52.2% (ep5-heavy) — not shrunk, not marketed

### Honest framing in the product

- UI **headline** numbers (Dashboard banner, landing Performance, Top
  Picks hero, Alpha Signals header) display the `live_*` target.
- **Tooltip** on each metric reveals the back-test origin and the
  shrinkage rationale.
- **BacktestSummary** card on Top Picks explicitly labels back-test
  numbers as "(audit only)" in smaller muted type.
- **PageGuide** on Alpha Signals has dedicated sections *"Why ~55% and
  not 64.3%?"* and *"Why ~1.3 Sharpe and not 8.04?"* with coin-flip
  analogies and Medallion Fund benchmarks.

This is "radical honesty" mode. Rationale: 8.04 Sharpe would be
higher than any fund in public records. Publishing it as the primary
number would either (a) mislead novice users or (b) get dismissed by
sophisticated evaluators. Publishing a defensible 1.3 gets us a fair
hearing in both audiences.

---

## 9. Known Weaknesses

1. **Short / SELL signals are un-tradeable.** The back-test bottom-20
   short strategy lost money across multiple epochs. The model's
   directional accuracy on "will it go down" is worse than on "will it
   go up". We therefore do NOT publish short signals — only
   AVOID-labelled rows in UI, no actual recommendation to borrow.

2. **1-day direction is random** (48.8% → coin flip). The model captures
   multi-week drift, not day-to-day noise. We explicitly don't market
   1-day DirAcc.

3. **1-month MAPE is too wide for price targets.** 12.49% error on a
   ±$100 stock means the target can be off by ~$12. The UI shows the
   median but warns (for `|return_1m| > 30%`) that the dollar number
   shouldn't be taken literally — use the rank tier instead.

4. **Extreme SELL forecasts on momentum stocks.** Stocks that rallied
   4–16× off their 52-week low (LITE $51→$850, COHR $55→$345, etc.) get
   -80% to -90% predicted returns. Direction is probably right
   (mean-reversion is real), magnitude is not. The ticker page shows a
   warning chip when |1m return| > 30% explaining this.

5. **Model is systematically bearish.** Mean 1-day prediction on
   training data = −3.5% vs real +0.1%. Explains why in live inference
   ~71% of signals are SELL and only ~25% are BUY. Artifact of the
   2020–2024 training period containing multiple corrections.

6. **No walk-forward validation.** Test was a single 23-day window. A
   rolling walk-forward (train up to T, test T→T+N, shift, repeat) was
   scoped into the roadmap as NB07 but not run. All our metrics should
   be read as "one market regime" not "generalises across regimes".

7. **No hyperparameter search.** `hidden_size=256` was chosen by A100
   memory budget; `lr=3e-4` and `dropout=0.1` are reasonable defaults,
   not Optuna-tuned.

---

## 10. Model Artifacts

All in `models/`:

| File | Size | Notes |
|---|---|---|
| `tft-epoch=02-val_loss=8.8051.ckpt` | 188 MB | ensemble member (best ConfLong) — **gitignored** |
| `tft-epoch=04-val_loss=9.2586.ckpt` | 188 MB | ensemble member (best MAPE 1d) — **gitignored** |
| `tft-epoch=05-val_loss=9.3008.ckpt` | 188 MB | primary model (best Top-20) — **gitignored** |
| `config.json` | 20 KB | features list, cutoffs, ticker metadata |
| `training_dataset_params.pkl` | 64 KB | GroupNormalizer, categorical encoders |
| `pca_model.pkl` | 208 KB | IncrementalPCA(n=32) for FinBERT |
| `old_model_sp500_tickers.txt` | 4 KB | **346 tickers** — the live universe |
| `old_model_400_tickers.txt` | 4 KB | 400 training tickers |
| `08_live_inference_pipeline.ipynb` | 200 KB | reference notebook from training |

SHA256 hashes for the 3 production checkpoints are verified on load
(in `services/model_loader.py`). Mismatch logs a warning but doesn't
block startup.

### Retrain workflow (when we do it)

1. Generate new checkpoints via notebooks 05–07.
2. Re-run the ensemble study (NB09) to pick the best 3.
3. Update `ENSEMBLE_CKPTS` in `services/model_loader.py`.
4. Update `CKPT_SHA256` with new hashes.
5. Update `MODEL_METRICS` in `frontend/src/lib/model-metrics.ts`:
   - Raw back-test numbers → `backtest_*` fields
   - Apply shrinkage → `live_*` fields (see §8)
6. Update `forecast.model_versions.metrics` JSONB in the DB.
7. Update `CLAUDE.md` metrics table and `docs/MODEL.md` (this file).

---

## 11. References

- **Paper:** [Lim et al., 2019 — Temporal Fusion Transformers](https://arxiv.org/abs/1912.09363)
- **Library:** [pytorch-forecasting](https://pytorch-forecasting.readthedocs.io/)
- **Training notebooks:** `models/08_live_inference_pipeline.ipynb` (the
  one we have locally). Full training notebooks (NB01–NB09) in the
  training workspace, not this repo.
- **Internal notes:** `docs/ENSEMBLE_NOTES.md`
- **Architecture:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
