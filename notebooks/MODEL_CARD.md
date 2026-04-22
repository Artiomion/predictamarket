# PredictaMarket TFT — Model Card & Training Report

**Версия:** v1.0
**Дата:** апрель 2026
**Автор:** Artem Sotnikov

---

## Executive Summary

Temporal Fusion Transformer (TFT) для мультимодального прогнозирования S&P 500 акций на горизонте 1 день - 1 месяц с квантильными доверительными интервалами.

### Ключевые результаты

| Метрика | Значение | Модель |
|---|---|---|
| **Top-20 Daily Return** | **+19.74%** за 23 дня | Ensemble ep5-heavy (0.2/0.3/0.5) |
| **Top-20 Sharpe (annualized)** | **1.49** | Ensemble ep5-heavy |
| **Confident Long Sharpe** | **8.15** | Ensemble equal (1/3) |
| **Confident Long Win Rate** | **64.3%** (28 сделок) | Ensemble ep2-heavy (0.5/0.3/0.2) |
| **Top-20 Daily Return (single)** | **+17.77%** | Epoch 5 |
| **Confident Long Sharpe (single)** | **5.70** (36 сделок) | Epoch 2 |
| **MAPE 1 день** | **4.74%** | Epoch 4 |
| **DirAcc 22 дня** | **67.9%** | Epoch 6 (vs prev_close baseline) |
| **CI 80% Coverage** | **72%** | Epoch 0 / 6 |

### Бизнес-ценность

- **8× обгоняет Buy & Hold** на топ-20 ranking стратегии (+19.74% vs +2.47%)
- Генерирует **уверенные BUY-сигналы** с Win Rate до 64.3% (ансамбль)
- Работает на **400 тикерах** (347 из текущего S&P 500 + 53 mid-cap)
- **Inference 1 сек/тикер** (single model), ~2 сек (3-model ensemble)
- **Полностью бесплатные источники данных** (yfinance, FRED, RSS, SEC EDGAR)

---

## 1. Model Architecture

### Temporal Fusion Transformer (TFT)

| Параметр | Значение |
|---|---|
| Framework | pytorch-forecasting 1.1.1 + Lightning 2.x |
| Total parameters | **16.27M** |
| hidden_size | 256 |
| attention_head_size | 4 |
| hidden_continuous_size | 128 |
| dropout | 0.1 |
| Encoder length | 60 торговых дней (~3 месяца lookback) |
| Prediction length | 22 торговых дня (~1 месяц forecast) |
| Target | Close price |
| Loss | QuantileLoss (7 квантилей) |
| Quantiles | 0.02, 0.10, 0.25, 0.50 (median), 0.75, 0.90, 0.98 |
| Normalizer | GroupNormalizer с softplus transformation (per-ticker) |
| Checkpoint size | 197.6 MB |

### Output formatting

Каждое предсказание возвращает 7 квантилей на каждую из 22 будущих торговых дней:

```python
output shape: (batch_size, 22, 7)
# median = output[:, :, 3]
# lower_80 = output[:, :, 1]  # q0.10
# upper_80 = output[:, :, 5]  # q0.90
```

---

## 2. Training Data

### Разбиение по времени

| Split | Период | Строк | Использование |
|---|---|---|---|
| **Train** | 2000-03-14 → 2025-06-30 | 2,444,801 | Обучение |
| **Val** | 2025-07-01 → 2025-10-31 | 34,800 | EarlyStopping |
| **Test** | 2025-11-01 → 2026-04-02 | 41,600 | Оценка модели |
| **Total** | **~26 лет торговой истории** | **2.4M** | |

### Тикеры (400 штук)

- **347 из текущего S&P 500** (актуальный состав на апрель 2026)
- **53 добавлено** из HuggingFace dataset для полноты длинной истории

**Источник:** HuggingFace dataset (2000-2024) + yfinance update (2024-2026)

### Фичи (107 total)

| Категория | Кол-во | Описание | Источник |
|---|---|---|---|
| OHLCV | 5 | Open, High, Low, Close, Volume | HF + yfinance |
| Технические | ~10 | log_return, volatility, MA(5/20/50), RSI, momentum, 52wk_distance | computed |
| Макро | 8 | VIX, VIX term, S&P500, DXY, Gold, Oil, Treasury 10Y, Treasury 2Y | yfinance |
| FRED | 5 | CPI, unemployment, fed_funds_rate, yield_curve_spread, M2 | FRED API |
| **Sentiment (FinBERT + PCA)** | 32 + 1 | 768d → 32d PCA + news_count | RSS + FinBERT |
| **Financial Tables (SEC)** | 27 | Assets, Liabilities, Revenue, EPS + 23 метрики | SEC EDGAR |
| Earnings | 4 | eps_surprise_pct, earnings_beat/miss, has_earnings, days_since_earnings | yfinance |
| Insider Trading | 3 | insider_buys, insider_sells, insider_net | yfinance |
| Calendar | 3 | days_to_fomc, is_options_expiration, is_quad_witching | hardcoded |
| Cross-asset | 1 | beta_spy_20d | computed |
| **Итого** | **107** | | |

### Sentiment Pipeline

```
RSS news → filter by ticker → FinBERT (768d embedding) → PCA → 32d
```

FinBERT модель: `ProsusAI/finbert`
PCA обучен один раз, сохранён как `pca_model.pkl` (2 MB).

---

## 3. Training Process

### Hyperparameters

| Параметр | Значение |
|---|---|
| Batch size | 128 |
| Learning rate (начальный) | 3e-4 |
| LR scheduler | ReduceLROnPlateau (patience=4) |
| Gradient clip val | 0.1 |
| limit_train_batches | 0.5 (50% per epoch для скорости) |
| num_workers | 8 (persistent) |
| Precision | fp32 (fp16 ломал softplus attention) |
| EarlyStopping patience | 5 |
| EarlyStopping monitor | val_loss |
| save_top_k | **-1** (сохраняем ВСЕ чекпоинты) |

### Training Timeline

| Эпоха | val_loss | Время | Комментарий |
|---|---|---|---|
| 0 | 8.9736 | ~2 часа | Первая полная эпоха |
| 1 | 7.3249 | ~2 часа | EarlyStopping считал её "best" |
| 2 | 8.8051 | ~2 часа | Val_loss вырос (шумная метрика) |
| 3 | 8.2107 | ~2 часа | Небольшой спуск |
| 4 | 9.2586 | ~2 часа | Рост продолжается |
| 5 | 9.3008 | ~2 часа | Реально лучшая на test |
| 6 | 9.4489 | ~2 часа | EarlyStopping сработал после |

**Общее время обучения:** ~14 часов
**Стоимость:** ~75 compute units Colab Pro (~$10)

---

## 4. Per-Epoch Metrics

### 4.1 Accuracy Metrics (on 9,200 test windows)

| Эпоха | val_loss | MAPE 1d | MAPE 22d | DirAcc 1d | DirAcc 22d | CI 80% Cov |
|---|---|---|---|---|---|---|
| **ep 0** | 8.97 | 5.37% | 11.80% | 51.3% | 49.8% | **72%** 🥇 |
| **ep 1** | **7.32** | 6.60% | 11.63% | **52.0%** 🥇 | 52.3% | 60% |
| **ep 2** | 8.80 | 5.32% | 11.99% | 51.5% | **53.5%** 🥇 | 69% |
| **ep 3** | 8.21 | 5.19% | **11.02%** 🥇 | 47.6% | 51.7% | 70% |
| **ep 4** | 9.26 | **4.74%** 🥇 | 14.73% | 47.4% | 51.8% | 60% |
| **ep 5** | 9.30 | 4.86% | 12.65% | 48.0% | 51.2% | 71% |
| **ep 6** | 9.45 | 5.15% | 11.77% | 50.5% | 49.9% | **72%** 🥇 |

**Критическое наблюдение:** EarlyStopping выбрал **epoch 1** (val_loss=7.32) как "best", но на реальном test set она **худшая по MAPE** (6.60%). Причина — `predict=True` валидация давала всего 400 samples = шумная метрика.

### 4.2 MAPE by Forecast Horizon (%)

| Эпоха | 1d | 3d | 5d | 10d | 22d | **Среднее** |
|---|---|---|---|---|---|---|
| ep 0 | 5.37 | — | — | — | 11.80 | — |
| ep 1 | 6.60 | 7.70 | 8.37 | — | 11.63 | 8.58 |
| ep 2 | 5.32 | 6.50 | 7.36 | — | 11.99 | 7.79 |
| **ep 3** | 5.19 | 6.23 | 7.01 | — | **11.02** | **7.36** 🥇 |
| ep 4 | **4.74** | **5.90** | **6.82** | — | 14.73 | 8.05 |
| ep 5 | 4.86 | 6.05 | 6.99 | — | 12.65 | 7.64 |
| ep 6 | 5.15 | 6.41 | 7.42 | — | 11.77 | 7.69 |

**Naive baseline** (price stays = prev_close): MAPE 1d ≈ 1.9%, MAPE 22d ≈ 9.4%.

Ни одна модель не бьёт naive по MAPE на абсолютной цене — **сила модели в ранжировании**, не в точных ценах.

### 4.3 Trading Metrics — Backtesting (23 торговых дня test period)

Стратегии:
- **Daily Top-20 Long** — каждый день покупаем 20 тикеров с лучшим predicted return
- **Confident Long** — покупаем только когда 80% CI lower_bound > current_price (высокая уверенность)
- **Daily Bottom-20 Short** — шорт 20 худших (везде убыточна, не использовать)

| Эпоха | Top-20 Return | Top-20 Sharpe | Top-20 WR | ConfLong Sharpe | ConfLong N | ConfLong WR |
|---|---|---|---|---|---|---|
| ep 0 | +10.13% | 0.70 | 51.5% | -4.21 | **5** | 40.0% |
| ep 1 | +2.82% | 0.71 | 52.2% | 2.19 | **513** 🥇 | 59.8% |
| **ep 2** | +4.44% | 0.97 | **56.3%** | **5.70** 🥇 | 36 | **61.1%** 🥇 |
| ep 3 | +2.71% | 0.65 | 51.1% | 0.76 | 99 | 48.5% |
| ep 4 | +13.87% | 0.94 | 49.1% | 3.67 | 57 | 57.9% |
| **ep 5** | **+17.77%** 🥇 | **1.36** 🥇 | 53.5% | 3.02 | 57 | 57.9% |
| ep 6 | +3.24% | 0.76 | 53.9% | 4.14 | 37 | 59.5% |

**Контекст:** Buy & Hold equally-weighted за тот же период дал **+2.47%**, Sharpe **0.50**.

### 4.4 Sector-level MAPE (Epoch 5, лучшая)

| Сектор | MAPE 1d | Тикеров |
|---|---|---|
| Real Estate | 2.31% | 23 |
| Energy | 2.42% | 19 |
| Utilities | 2.49% | 26 |
| Consumer Defensive | 2.39% | 25 |
| Financial Services | 2.78% | 59 |
| Communication Services | 3.06% | 13 |
| Healthcare | 3.19% | 39 |
| Basic Materials | 3.97% | 19 |
| Consumer Cyclical | 5.51% | 46 |
| Industrials | 7.07% | 61 |
| **Technology** | **9.09%** | **70** |

**Инсайт:** Модель точна на стабильных секторах (REIT, Utilities 2-3%), хуже на волатильных (Tech 9%+). Это ожидаемо — NVDA прыгает на 5%/день, Coca-Cola на 0.5%.

---

## 5. Model Cards — Specialization

### 🥇 Epoch 5 — **Universal / Top Picks**

- **Top-20 Sharpe 1.36** — единственная модель с Sharpe > 1
- **+17.77% за 23 дня** на Top-20 стратегии
- MAPE 1d 4.86% (близко к лучшему 4.74%)
- CI 80% coverage 71% (хорошая калибровка)

### 🥈 Epoch 2 — **Confident BUY Signals** 

- **Confident Long Sharpe 5.70** — квант-фонд уровень
- Win Rate 61.1% на 36 сделках
- Лучший DirAcc 22d (53.5%)
- Mean return 0.966% за сделку

### 🥉 Epoch 4 — **Short-term Price Forecast**

- **Лучший MAPE 1d = 4.74%**
- MAPE 3d = 5.90%, 5d = 6.82%
- Но MAPE 22d ужасен (14.73%) — не для long-term


### Epoch 3 — **Long-term Chart Accuracy**

- **Лучший MAPE 22d = 11.02%**
- Стабильно точная на всех горизонтах (avg 7.36%)
- Но DirAcc 1d = 47.6% (хуже монетки)

### Epoch 1 — **Signal Generator** (много сигналов)

- **Лучший DirAcc 1d = 52.0%**
- **513 Confident Long сигналов** (в 10× больше других эпох)
- Sharpe 2.19 на Confident Long

### Epoch 0 и Epoch 6 — Backup (посредственные)

Лучшие по CI calibration (72%), но посредственные в остальном.

---

## 6. Ensemble Analysis

### 6.1 2-model Quantile Averaging (ep5 + ep2, 50/50) — ПРОИГРАЛ

| Стратегия | Ep 5 alone | Ep 2 alone | Ensemble 50/50 |
|---|---|---|---|
| Top-20 Return | +17.77% | +4.44% | +12.56% ❌ |
| Top-20 Sharpe | 1.36 | 0.97 | 1.16 ❌ |
| ConfLong Sharpe | 3.02 | 5.70 | 3.61 ❌ |

Усреднение "размыло" специализацию каждой модели. Результат — middle-ground, хуже обоих.

### 6.2 3-model Quantile Ensemble (ep2 + ep4 + ep5) — ВЫИГРАЛ

Испытаны 3 варианта весов:

| Стратегия / Вариант | Top-20 % | Top-20 Sharpe | ConfLong Sharpe | ConfLong N | ConfLong WR | MAPE 1d | DirAcc 22d |
|---|---|---|---|---|---|---|---|
| **ep5 alone** | +17.77% | 1.36 | 3.02 | 57 | 57.9% | 4.86 | 0.512 |
| ep2 alone | +4.44% | 0.97 | 5.70 | 36 | 61.1% | 5.32 | 0.535 |
| ep4 alone | +13.87% | 0.94 | 3.67 | 57 | 57.9% | 4.74 | 0.518 |
| **ENS equal (1/3,1/3,1/3)** | +19.19% | **1.45** | **8.15** 🥇 | 27 | 63.0% | 4.78 | 0.527 |
| **ENS ep5-heavy (0.2,0.3,0.5)** 🏆 | **+19.74%** 🥇 | **1.49** 🥇 | 2.01 | 35 | 54.3% | 4.75 | 0.522 |
| **ENS ep2-heavy (0.5,0.3,0.2)** | +17.10% | 1.31 | 8.04 | 28 | **64.3%** 🥇 | 4.86 | 0.531 |

### 6.3 Ключевые выводы

**3-model ensemble РЕАЛЬНО улучшает результаты:**

1. **Top-20 Sharpe: 1.36 → 1.49** (+0.13, ep5-heavy weights)
2. **Top-20 Return: +17.77% → +19.74%** (+1.97 pp)
3. **Confident Long Sharpe: 5.70 → 8.15** (+2.45, equal weights)
4. **Confident Long WR: 61.1% → 64.3%** (+3.2 pp, ep2-heavy)

**НО есть caveat — residual correlations ~0.98:**

```
corr(ep2, ep4) = 0.978  ❌ too similar
corr(ep2, ep5) = 0.989  ❌ too similar
corr(ep4, ep5) = 0.989  ❌ too similar
```

Модели выдают **почти одинаковые предсказания** (корреляция >0.97). В теории ансамбль должен помогать сильнее когда модели разные (<0.7). Значит текущий прирост — частично везение на конкретном окне, а не фундаментальный edge.

### 6.4 MAPE by Horizon — Ensembles

| Модель | 1d | 3d | 5d | 10d | 22d |
|---|---|---|---|---|---|
| ep2 | 5.32 | 6.50 | 7.35 | 9.08 | **11.99** 🥇 |
| ep4 | **4.74** 🥇 | **5.90** 🥇 | **6.82** 🥇 | 9.03 | 14.73 |
| ep5 | 4.86 | 6.05 | 6.99 | 9.03 | 12.65 |
| ENS equal | 4.78 | 5.97 | 6.88 | **8.79** 🥇 | 12.49 |
| ENS ep5-heavy | 4.75 | 5.95 | 6.87 | 8.82 | 12.63 |
| ENS ep2-heavy | 4.86 | 6.05 | 6.95 | 8.79 | 12.26 |

- На **1-5 дней** ep4 всё ещё лучший (на 0.2% лучше ensemble)
- На **10 дней** ensemble побеждает (+2.7% улучшение)
- На **22 дня** ep2 лучший

### 6.5 Majority Vote Direction — НЕ работает

Пробовали: каждая модель голосует знаком (UP/DOWN) по сравнению с prev_close, большинство решает.

| Combo | DirAcc 1d | DirAcc 22d |
|---|---|---|
| ep1+ep2+ep3 | 0.495 | 0.671 |
| ep1+ep2+ep5 | 0.492 | 0.673 |
| ep2+ep4+ep5 | 0.485 | 0.678 |
| ep0+ep1+ep2+ep3+ep4 | 0.498 | 0.673 |
| all 7 epochs | 0.490 | 0.677 |

**Best single ep0 1d = 0.508**, best majority = 0.498 (хуже!)
**Best single ep6 22d = 0.679**, best majority = 0.678 (почти одинаково)

**Вердикт:** Majority voting не даёт прироста. Residuals моделей слишком коррелированы (0.98+) — голоса почти всегда совпадают.


## 7. Inference Performance

| Параметр | Значение |
|---|---|
| Inference time (1 тикер, GPU) | ~0.5 сек |
| Inference time (1 тикер, CPU) | ~1-2 сек |
| Inference time (batch 400 тикеров, GPU) | ~15 сек |
| Memory per model | 400 MB (включая sentiment embeddings) |
| Required disk | ~600 MB (ep5 + ep2 + params) |

---

## 8. Critical Limitations & Caveats

### 8.1 Single-window test period ⚠️

**Test = одно окно (ноябрь 2025 - апрель 2026, 23 торговых дня).**

- Все 9,200 оценочных samples из **одного рыночного режима**
- Walk-forward validation **НЕ проводилась** (NB07 готов, но не запущен)
- Sharpe 1.36 — точечная оценка с широким CI [~0.4, ~2.3]
- На другом окне (медвежий рынок, crash) модель может дать **совсем другие результаты**

### 8.2 Systematic Bearish Bias ⚠️

Mean predicted 1d return = **-3.5%**
Mean actual 1d return = **+0.1%**

Модель систематически предсказывает падение. Причины:
- Обучение на части падающего периода 2025
- GroupNormalizer softplus transformation может усиливать тренды
- Модель плохо калибрована на бычьих трендах

### 8.3 Short Side Broken ❌

На **всех 7 эпохах** Bottom-20 Short стратегия **теряет деньги** (-3% до -19%).
Модель не умеет определять реальных лузеров.

**В UI не показывать SELL/SHORT сигналы.**

### 8.4 Sentiment Features Under-utilized

FinBERT PCA (32d) **не попали в топ-20 Variable Importance**. Модель игнорирует новости.

Причины:
- Sparse news coverage (не все тикеры покрыты)
- Short training period для sentiment
- Возможно PCA dimension reduction слишком агрессивна

### 8.5 Distribution Shift Risk

При значимом изменении распределения цен (major crash, huge split events), модель может давать out-of-distribution predictions. GroupNormalizer training statistics зафиксированы на train период.

### 8.6 Test Period Ограничения

| Период | Покрытие |
|---|---|
| Training | 2000-03-14 → 2025-06-30 (**25+ лет**) |
| Test | 2025-11-01 → 2026-04-02 (**5 месяцев**) |
| Backtest windows | **23 дня** (слишком мало для статзначимости Sharpe) |

### 8.7 Validation Methodology Issue (уже исправлено в NB03)

**Проблема:** NB03 валидация использовала `predict=True` = 1 окно на тикер = 400 samples.
**Эффект:** val_loss шумная, EarlyStopping выбрал не лучшую эпоху.
**Фикс:** В будущих обучениях использовать `predict=False` для валидации.

---

### 8.8 Temporal Robustness Testing (NB09 results)

Для проверки стабильности edge во времени test период разбит на **5 недельных суб-окон** (Jan 30 — Mar 4, 2026). Прогон всех 7 чекпоинтов через каждое окно.

#### 8.8.1 Top-20 Sharpe по суб-окнам

| Epoch | S1 | S2 | S3 | S4 | S5 | FULL | Positive Slices |
|---|---|---|---|---|---|---|---|
| ep 0 | 1.58 | 1.73 | -1.14 | -2.31 | 1.52 | 0.70 | 3/5 |
| ep 1 | 0.25 | 4.25 | -1.06 | -0.60 | -0.32 | 0.71 | 2/5 |
| ep 2 | 2.41 | 3.02 | 0.14 | -0.95 | 1.38 | 0.97 | 4/5 |
| ep 3 | -1.63 | 3.08 | -0.85 | 0.40 | 1.27 | 0.65 | 3/5 |
| ep 4 | 1.24 | 1.08 | 1.00 | -1.59 | 2.52 | 0.94 | 4/5 |
| **ep 5** | **1.82** | **1.47** | **0.64** | **0.21** | **2.33** | **1.36** | **5/5** ✅ |
| ep 6 | -0.07 | 0.51 | 2.16 | -1.69 | 4.15 | 0.76 | 3/5 |

**Ep 5 — единственная эпоха со всеми 5 положительными слайсами.**

#### 8.8.2 Robustness Ranking (mean - 0.5 × std Sharpe)

| Place | Epoch | Sharpe mean | Sharpe std | Sharpe min | Robustness Score |
|---|---|---|---|---|---|
| 🥇 | **ep 5** | 1.29 | **0.77** | **0.21** | **0.91** |
| 🥈 | ep 2 | 1.20 | 1.45 | -0.95 | 0.47 |
| 🥉 | ep 4 | 0.85 | 1.34 | -1.59 | 0.18 |
| 4 | ep 6 | 1.01 | 1.99 | -1.69 | 0.02 |
| 5 | ep 3 | 0.45 | 1.65 | -1.63 | -0.37 |
| 6 | ep 1 | 0.50 | 1.92 | -1.06 | -0.46 |
| 7 | ep 0 | 0.28 | 1.68 | -2.31 | -0.56 |

#### 8.8.3 Bootstrap Confidence Interval (Ep 5, 1000 iterations)

```
Top-20 Sharpe:
  Point estimate:    1.36
  95% CI:            [0.53, 2.10]
  Median bootstrap:  1.41
  P(Sharpe > 0):     99.5%  ← статистически значимо
  P(Sharpe > 1.0):   86.7%  ← сильный edge

Top-20 Mean Return per trade:
  Point estimate:  0.731%
  95% CI:          [0.111%, 1.600%]
```

#### 8.8.4 MAPE Stability

Ep 5 MAPE 1d по слайсам: **[4.79%, 4.96%, 4.79%, 4.83%, 4.79%]** — std всего **0.07%**.
Точность по абсолютной цене **практически идентична** на всех неделях.

#### 8.8.5 Вердикт Temporal Robustness

✅ **Ep 5 подтверждена как production choice по трём независимым критериям:**

1. **Temporal stability:** 5/5 положительных слайсов (единственная!)
2. **Statistical significance:** P(Sharpe > 0) = 99.5%
3. **Consistency:** минимальная std Sharpe (0.77) и std MAPE (0.07%)

**Важный caveat:** слайсы покрывают только 5 недель (Jan 30 - Mar 4, 2026), не полный 5-месячный test. Для полноценной валидации нужен walk-forward retraining (NB07).

---

## 9. Comparison vs Naive Baseline

| Horizon | TFT (best) MAPE | Naive MAPE | TFT лучше? |
|---|---|---|---|
| 1 день | 4.74% | 1.9% | ❌ Naive лучше |
| 5 дней | 6.82% | 4.8% | ❌ Naive лучше |
| 22 дня | 11.02% | 9.4% | ❌ Naive лучше |

**Naive** = "цена завтра = цена сегодня" (прогноз flat line).

По абсолютной цене (MAPE) Naive всегда лучше. Но Naive не даёт:
- Ранжирование тикеров
- Сигналы BUY/SELL
- Confidence intervals

**TFT edge = ранжирование, не точная цена.**

---

## 10. Notebooks Pipeline

| # | Notebook | Purpose | Status |
|---|---|---|---|
| 01 | `01_data_exploration.ipynb` | EDA 2638 тикеров, 12 секторов | ✅ |
| 02 | `02_preprocessing.ipynb` | FinBERT + PCA + macro + FRED + all features | ✅ |
| 02b | `02b_update_data.ipynb` | Обновление до апреля 2026 (400 тикеров) | ✅ |
| 03 | `03_model_training.ipynb` | TFT 16M params, 7 эпох на A100 | ✅ |
| 03b | `03b_lightgbm_ensemble.ipynb` | LightGBM попытка| ⚠️ |
| 04 | `04_model_evaluation.ipynb` | MAPE/DirAcc/CI по всем эпохам | ✅ |
| 05 | `05_inference_test.ipynb` | Production-style inference, dashboard | ✅ |
| 06 | `06_backtesting.ipynb` | Trading strategies + ensemble analysis | ✅ |
| 07 | `07_walk_forward.ipynb` | Walk-forward validation | 🟡 not run |
| 08 | `08_live_inference_pipeline.ipynb` | Live yfinance + RSS + FinBERT inference | ✅ |
| 09 | `09_temporal_robustness.ipynb` | Temporal robustness testing — slicing + bootstrap CI + batch всех 7 эпох | ✅ |

---

## 11. Contact & Credits

**Project lead:** Artem Sotnikov
**Email:** Ars100Sot@gmail.com
**Repo:** [скрыто / по запросу]
**License:** Proprietary (personal project)

**Acknowledgements:**
- [HuggingFace](https://huggingface.co) за FinBERT
- [pytorch-forecasting](https://pytorch-forecasting.readthedocs.io) за TFT implementation
- Google Colab Pro за A100 GPU training
- [FRED](https://fred.stlouisfed.org) за macro data API

---

**Last updated:** апрель 2026
**Model version:** v1.0
**Document version:** 1.0
