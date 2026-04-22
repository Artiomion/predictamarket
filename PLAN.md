# PredictaMarket

Платформа мультимодального прогнозирования акций

## Общие сведения

| | |
|---|---|
| **Тип проекта** | Pet-project |
| **Назначение** | Веб-платформа для инвесторов — аналог CoinMarketCap для акций с AI-прогнозами |
| **Уникальная фича** | Мультимодальный ML-прогноз + ранжирование акций + доверительные интервалы |
| **Рынок** | S&P 500 (США) — **318 активных тикеров** (346 в модели ∩ S&P 500, минус 28 из 36-ticker blocklist где post-split / corporate-action data mismatch) |
| **Статус** | Фазы 1-3 завершены (ML + Backend + Frontend). Фаза 4 (polish + launch) в работе. |

---

## 1. Описание продукта

PredictaMarket — веб-сервис для инвесторов, позволяющий отслеживать портфель и получать AI-прогнозы стоимости акций. Платформа агрегирует рыночные данные, финансовые отчёты, макроэкономику и новостной поток, передавая их мультимодальной модели для построения прогноза.

### Проблема рынка

- Bloomberg Terminal стоит $2 000+/мес — недоступен частному инвестору
- TradingView не имеет AI-прогнозов и объяснения причин движения
- Yahoo Finance / Google Finance — устаревший UI, нет AI
- Существующие AI-прогнозы статичны и не обновляются при выходе новостей
- Информация разбросана по десяткам сервисов: котировки отдельно, новости отдельно, отчётность отдельно

### Решение

- Профессиональные инструменты анализа по цене $15-39 в месяц
- AI-прогноз учитывает технику + новости + отчётность + макроэкономику одновременно
- Динамический прогноз — пересчитывается при каждой важной новости
- Объяснимый AI (XAI) — пользователь видит, какие факторы повлияли на прогноз
- Единое окно: всё об акции — цена, прогноз, новости, отчётность, инсайдеры — в одном месте

### Ключевые возможности (обзор)

- Каталог **318 акций** S&P 500 с котировками в реальном времени (WebSocket + yfinance poll каждые 30 сек для активных подписок)
- AI-прогноз на горизонт 1д / 3д / 1нед / 2нед / 1мес с доверительным интервалом 80% и 95%
- **AI-ранжирование (Top Picks)** — ep5-heavy ensemble [0.2/0.3/0.5]. Back-test Sharpe 1.49 на Top-20 (live target ~1.0 после shrinkage)
- **Alpha Signals (Premium)** — ep2-heavy ensemble [0.5/0.3/0.2]. Back-test Win Rate 64.3% на consensus BUY (live target ~56%)
- **Торговые сигналы**: BUY / SELL / HOLD с уровнем уверенности HIGH / MEDIUM / LOW
- "Top Picks" — топ-10/20 акций по predicted return, фильтр по positive return + BUY signal
- Профессиональные candlestick-графики с техническим анализом и прогноз overlay
- Финансовые показатели компании и отчётность SEC EDGAR
- Управление портфелем с продвинутой аналитикой
- Новостной агрегатор с AI-sentiment
- Earnings Calendar и Insider Transactions
- Watchlist с уведомлениями

---

## 2. ML-система (реализовано)

### Модель: Temporal Fusion Transformer (TFT)

| Параметр | Значение |
|---|---|
| Архитектура | TFT (pytorch-forecasting) |
| hidden_size | 256 |
| attention_heads | 4 |
| Параметры | 16.3M |
| Encoder length | 60 торговых дней (~3 месяца lookback) |
| Prediction length | 22 торговых дня (~1 месяц вперёд) |
| Output | 7 квантилей (0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98) |

> **Примечание по доверительным интервалам:**
> - 80% CI = диапазон между квантилями 0.1 и 0.9 (уже в API)
> - 95% CI ≈ диапазон между квантилями 0.02 и 0.98 (фактически ~96%, что достаточно близко к 95%). Модель уже считает эти квантили — нужно просто добавить их в JSON-ответ API как `lower_95` / `upper_95`. Переобучение не требуется.
| Тикеры обучения | 400 (из 2,638 в HuggingFace датасете) |
| Тикеры в сервисе | **318 активно** (346 S&P 500 ∩ модель − 28 blocklist). См. `docs/MODEL.md §9` про split-adjustment blocklist. |
| Данные | 2000-03-14 — 2026-04-02 (~2.4M строк train, 9200 test windows post-Oct-2025) |
| Primary checkpoint | `tft-epoch=05-val_loss=9.3008.ckpt` (ep5) |
| Ensemble (per-surface) | ep5-heavy [0.2/0.3/0.5] для Top Picks · ep2-heavy [0.5/0.3/0.2] для Alpha Signals |

### Входные данные (107 фичей)

| Модальность | Фичи | Источник |
|---|---|---|
| Time Series | OHLCV, log_return, volatility, MA(5/20/50), RSI, momentum, 52wk proximity | HuggingFace dataset + yfinance |
| Макро | S&P500, VIX, VIX term structure, Treasury 10Y, DXY, Gold, Oil | yfinance |
| FRED | CPI, unemployment, fed_funds_rate, yield_curve_spread, M2 money supply | FRED API |
| Sentiment | FinBERT 768d -> PCA 32d из новостей (32 компонента + news_count) | HuggingFace dataset + RSS |
| Финансовые таблицы | 27 метрик SEC (Assets, Liabilities, Revenue, EPS и др.) | HuggingFace dataset |
| Earnings | eps_surprise_pct, earnings_beat/miss, has_earnings, days_since_earnings | yfinance |
| Insider Trading | insider_buys, insider_sells, insider_net | yfinance |
| Calendar | days_to_fomc, is_options_expiration, is_quad_witching | hardcoded dates |
| Cross-asset | beta_spy_20d | computed |

### Текущие метрики (test window Nov 2025 — Apr 2026, N=9200, single window)

Две конфигурации ensemble оптимизируются отдельно под разные surface'ы. На UI показываются **live targets** (после heuristic shrinkage для single-window bias); raw back-test цифры доступны в caveat-тултипах.

**Top Picks — ep5-heavy [0.2/0.3/0.5]:**

| Метрика | Back-test | Live target (headline) |
|---|---|---|
| Top-20 Sharpe | 1.49 | **~1.0** |
| Top-20 Return (23 дня) | +19.74% | — |
| Alpha vs S&P 500 | +12.01pp | **~+4pp** |
| MAPE 1d | 4.75% | — |

**Alpha Signals — ep2-heavy [0.5/0.3/0.2] (Premium):**

| Метрика | Back-test | Live target |
|---|---|---|
| ConfLong Sharpe | 8.04 | **~1.3** (heavy shrinkage, N=28) |
| ConfLong Win Rate | 64.3% | **~56%** |
| N trades (back-test) | 28 | — |

**Shared (обе конфигурации):**

| Метрика | Значение | Комментарий |
|---|---|---|
| DirAcc 1d | 48.1% | Random — не маркетим |
| DirAcc 22d | 52.2% | Barely above random — **не маркетим** как strength |
| MAPE 22d | 12.63% | Слишком широко для price targets — используем для ranking/direction |
| Inference time | ~1 сек single / ~3 сек ensemble | Приемлемо |
| S&P 500 baseline | +7.73% / Sharpe 0.8 | Benchmark |

### Главная сила модели — ранжирование и conviction filter

**Ранжирование акций (Top Picks)** — ep5-heavy ensemble [0.2/0.3/0.5]. Back-test: Top-20 Sharpe 1.49, return +19.74%, alpha +12.01pp vs S&P 500. Live target после shrinkage — Sharpe ~1.0, alpha ~+4pp. Это и есть core value platform'ы.

**Conviction filter (Alpha Signals, Premium)** — ep2-heavy ensemble [0.5/0.3/0.2]. Когда `lower_80 > current_close` (все 3 модели согласны), WR 64.3% на 28 trades в back-test. Live target ~56% WR. Малая выборка — caveat в UI.

**Directional accuracy — НЕ маркетим.** DirAcc 1d = 48.1% (random), DirAcc 22d = 52.2% (едва выше coin flip). Ранее было предположение про 68% — это была ошибочная интерпретация другой метрики. Radical honesty mode: в UI не упоминается.

**Как это отражается в продукте:**
- **Top Picks** — главный экран. Модель выбирает 10-20 акций с максимальным predicted return + BUY signal + положительный 1m return.
- **Alpha Signals (Premium)** — отдельный feed ensemble-сигналов с conviction filter. Pro/Premium-only.
- **Ranking на Dashboard** — основная сортировка по predicted return, не по алфавиту/капе.
- **Доверительные интервалы** — 80% (лента) и 95% (полупрозрачная) на графике прогноза.
- **Waterfall Chart «Что повлияло»** — TFT variable importance → топ-5 факторов для каждого прогноза.
- **Extreme-forecast warning** — при `|predicted_return_1m| > 30%` UI показывает warning chip что dollar target ненадёжен, использовать rank tier вместо absolute price.

### Что нужно улучшить

- **Walk-forward валидация** — сейчас single test window (23 trading days). Нужно 3-5 rolling окон для уверенности что метрики держатся. Notebook 09_temporal_robustness начат, полноценный walk-forward (NB07) отложен на retrain.
- **Split-adjustment blocklist** — 28 S&P 500 тикеров (NVDA, AVGO, WMT, GE, GS и др.) заблокированы из-за post-split price mismatch. Снимается retrain'ом на split-adjusted prices.
- **Residual correlation между ensemble members** — corr(ep2,ep4)=0.978, corr(ep2,ep5)=0.989. Diversification bonus минимален. True ensemble требует независимых seeds.
- **Sentiment features largely unused** — 32 из 107 фичей (sent_0..sent_31 PCA) не попали в топ variable importance. Модель учится по OHLCV/technical/SEC financials, не по news. Либо дропнуть sentiment, либо weight'ить сильнее при retrain.
- **Model systematically bearish** — mean prediction 1d = −3.5% на обучающих данных при реальном +0.1%. В live inference ~71% сигналов SELL/AVOID. Baked в обучающее распределение (2020-2024 содержал много коррекций).
- **Hyperparameter tuning не запускался** — hidden_size=256 выбран по A100 memory, не Optuna. LR/dropout — reasonable defaults.
- **SEC coverage ~88-91%** на flagship тикерах (AAPL/NVDA/MSFT). ~12 XBRL концептов не у всех компаний.

### Jupyter Notebooks (в `notebooks/`, не в git)

| Ноутбук | Назначение |
|---|---|
| 01_data_exploration.ipynb | EDA HuggingFace датасета (2,638 тикеров) |
| 02b_update_data.ipynb | Обновление данных до Apr 2026 |
| 03_model_training.ipynb | TFT обучение (7 эпох сохранены, ep0..ep6) |
| 04_model_evaluation.ipynb | MAPE, DirAcc, CI coverage, ensemble study |
| 05_inference_test.ipynb | End-to-end inference validation |
| 06_backtesting.ipynb | Top-20 + ConfLong стратегии, Sharpe, alpha |
| 09_temporal_robustness.ipynb | Temporal stability (частичный walk-forward) |
| MODEL_CARD.md | Сводная модель-карта для внешнего аудита |

Live inference реализация — в `backend/forecast-service/services/inference.py`, не в ноутбуке.

### Артефакты модели (out-of-repo)

Все тяжёлые артефакты (`.ckpt`, `.pkl`, `config.json`, reference notebooks) исключены из git (IP + размер). Распространяются отдельно. Что хранится локально для работы сервисов:

```
models/
  tft-epoch=02-val_loss=8.8051.ckpt   — ensemble member (ep2, 188 MB)
  tft-epoch=04-val_loss=9.2586.ckpt   — ensemble member (ep4, 188 MB)
  tft-epoch=05-val_loss=9.3008.ckpt   — primary + ensemble (ep5, 188 MB)
  config.json                          — 107 фичей, 27 SEC метрик, cutoffs
  training_dataset_params.pkl          — TimeSeriesDataSet categorical_encoders/scalers/normalizer
  pca_model.pkl                        — IncrementalPCA(32) для FinBERT embeddings
  old_model_400_tickers.txt            — 400 тикеров обучения (в репо)
  old_model_sp500_tickers.txt          — 346 S&P 500 ∩ модель (в репо)
  blocklist_tickers.txt                — 36 blocklisted тикеров (в репо)
```

Фикс SHA256 чекпоинтов в `backend/forecast-service/services/model_loader.py` — проверка целостности при загрузке.

### API модели (output)

```json
{
  "ticker": "AAPL",
  "current_close": 255.92,
  "signal": "SELL",
  "confidence": "LOW",
  "forecast": {
    "1d":  {"median": 248.58, "lower_80": 220.44, "upper_80": 277.03, "lower_95": 210.00, "upper_95": 290.00},
    "3d":  {"median": 249.07, "lower_80": 220.23, "upper_80": 277.73, "lower_95": 208.50, "upper_95": 292.00},
    "1w":  {"median": 245.99, "lower_80": 216.54, "upper_80": 274.03, "lower_95": 205.00, "upper_95": 288.00},
    "2w":  {"median": 244.50, "lower_80": 210.00, "upper_80": 280.00, "lower_95": 198.00, "upper_95": 295.00},
    "1m":  {"median": 243.78, "lower_80": 200.27, "upper_80": 291.78, "lower_95": 185.00, "upper_95": 310.00},
    "3m":  {"median": 240.00, "lower_80": 185.00, "upper_80": 305.00, "lower_95": 165.00, "upper_95": 330.00}
  },
  "full_curve": [248.58, 249.07, ..., 243.78],
  "variable_importance": {
    "top_factors": [
      {"name": "RSI_14", "weight": 0.18, "direction": "bearish"},
      {"name": "earnings_surprise", "weight": 0.15, "direction": "bullish"},
      {"name": "VIX", "weight": 0.12, "direction": "bearish"},
      {"name": "insider_net", "weight": 0.09, "direction": "neutral"},
      {"name": "MA_50_cross", "weight": 0.08, "direction": "bearish"}
    ]
  },
  "news_articles_used": 20,
  "inference_time_s": 1.04
}
```

---

## 3. Функциональные модули платформы

### 3.1. Профессиональные графики и технический анализ

**Библиотека:** TradingView Lightweight Charts (бесплатная, open-source)

**Возможности:**
- Candlestick (OHLCV) с переключением таймфрейма: 1D / 1W / 1M / 3M / 1Y / 5Y / Max
- Индикаторы overlay: SMA(5/20/50/200), EMA, Bollinger Bands
- Индикаторы в отдельной панели: RSI, MACD, Volume
- Прогнозная линия TFT поверх графика (другой цвет, пунктирная)
- Доверительные интервалы 80% (плотная лента) и 95% (полупрозрачная лента)
- Метки на графике: новости (📰), earnings (📊), insider trades (👤), FOMC (🏛️)
- При наведении на метку — popup с деталями события
- Crosshair с привязкой к свече — дата, OHLCV, объём, прогноз в tooltip
- Полноэкранный режим графика
- Drawing tools: трендовые линии, горизонтальные уровни, Fibonacci retracement

### 3.2. Финансовые показатели компании

**Карточка компании (Company Profile):**
- Название, тикер, сектор, индустрия, логотип, описание
- Рыночная капитализация, P/E, P/S, P/B, EV/EBITDA
- Дивидендная доходность, payout ratio
- 52-week high/low, ATH
- Beta, short interest
- Количество сотрудников, дата IPO

**Ключевые метрики (Key Metrics) — дашборд карточек:**
- Revenue, Net Income, EPS, Free Cash Flow
- Profit Margin, ROE, ROA, Current Ratio, Debt/Equity
- YoY сравнение (стрелки ↑↓ с процентами)
- Sparkline-графики для каждой метрики за 8 кварталов

### 3.3. Финансовая отчётность (SEC EDGAR)

**Три таблицы с переключением:**
- **Income Statement** — Revenue, COGS, Gross Profit, Operating Income, Net Income, EPS
- **Balance Sheet** — Total Assets, Total Liabilities, Equity, Cash, Debt
- **Cash Flow Statement** — Operating CF, Investing CF, Financing CF, Free CF

**Формат представления:**
- Табличный вид: 4-8 кварталов или 3-5 лет (переключатель Quarterly / Annual)
- Каждая ячейка кликабельна — раскрывает детализацию
- YoY / QoQ изменения с цветовой индикацией (зелёный рост, красный падение)
- Скачивание в CSV/Excel

### 3.4. AI-прогноз (Forecast Engine) — главная фича

**Пользовательский сценарий:**
1. Открываешь страницу акции → нажимаешь «Build Forecast» (крупная кнопка с gradient)
2. Выбираешь горизонт: 1 день / 3 дня / 1 неделя / 2 недели / 1 месяц / 3 месяца
3. Анимация загрузки: прогресс-бар «Collecting market data → Analyzing news → Running TFT model → Done» (3-10 секунд)
4. На графике плавно дорисовывается прогнозная линия + доверительные интервалы 80% и 95%
5. Справа: карточка «What Moved the Prediction» — waterfall chart с топ-5 факторами и весами
6. При наведении на точку прогноза — popup с: медиана, CI 80%, CI 95%, ключевая новость/событие в эту дату
7. Signal badge: BUY/SELL/HOLD с confidence HIGH/LOW
8. Кнопка «Compare with previous forecast» — наложить прошлый прогноз для сравнения точности

**История прогнозов:**
- Таблица «Model history» — что модель предсказывала неделю/месяц назад
- Фактическая точность каждого прошлого прогноза (hit/miss CI)
- Средняя точность модели по данному тикеру
- График: прошлые прогнозы vs реальность — наглядная демонстрация качества

### 3.5. Top Picks — витрина силы модели

**Концепция:** Главный экран после Dashboard. Показывает конкурентное преимущество модели.

**Содержание:**
- Топ-5 (Free) / Топ-20 (Pro/Premium) акций по predicted return
- Для каждой акции: тикер, название, текущая цена, predicted return %, signal, confidence
- Фильтр: BUY signal + positive 1m return (иначе Top Picks выглядит broken с отрицательными returns)
- Badge «~56% Win Rate (live target)» на confident ensemble-сигналах
- Backtesting performance: Top-20 vs S&P 500 в тестовом окне (23 trading days)
- Обновляется каждый час (Airflow `dag_run_forecast`) через ep5-heavy ensemble

### 3.6. Управление портфелем

**Несколько портфелей:**
- Создание именованных портфелей: «Долгосрок», «Дивиденды», «Growth», и т.д.
- Каждый портфель с отдельным P&L и аналитикой
- Drag-and-drop позиций между портфелями

**Добавление позиций:**
- Тикер (autocomplete из 318 активных S&P 500)
- Количество акций
- Цена покупки (или текущая рыночная)
- Дата сделки
- Комиссия (опционально)
- Поддержка нескольких покупок одного актива по разным ценам → автоматический расчёт средней цены (усреднение)

**Portfolio Dashboard:**
- Общая стоимость портфеля (текущая)
- Total P&L в $ и % (all-time)
- Доходность с начала года (YTD)
- Доходность за 1д / 1нед / 1мес / 3мес / 1год
- Лучшая и худшая позиция дня

**Визуальная аналитика:**
- Круговая диаграмма (donut chart) распределения по секторам
- Круговая диаграмма распределения по компаниям (топ-10 + «Other»)
- Историческая доходность портфеля vs S&P 500 на одном графике (line chart, с начала отслеживания)
- Матрица корреляций активов (heatmap) — реальный уровень диверсификации
- Дивидендный календарь — ближайшие выплаты по активам из портфеля (timeline)
- Projected dividend income за год

**Экспорт:**
- История транзакций в CSV / Excel
- Полный отчёт портфеля в PDF

### 3.7. Watchlist

**Возможности:**
- Добавление акций в избранное одним кликом (иконка ★ на любой странице)
- Несколько вотчлистов (именованные)
- Компактная таблица: тикер, цена, изменение %, signal, confidence, sparkline
- Сортировка по любому столбцу
- Quick action: «Build Forecast» прямо из вотчлиста
- Push-уведомления при срабатывании алертов (ценовые уровни, смена сигнала)

### 3.8. Новостной агрегатор

**Лента новостей по акции:**
- RSS-источники: Reuters, Yahoo Finance, MarketWatch
- Каждая новость: заголовок, источник, время, sentiment score (позитивная 🟢 / нейтральная 🟡 / негативная 🔴)
- FinBERT confidence score (0.0 - 1.0) рядом с меткой
- Клик → раскрытие summary + ссылка на оригинал

**Агрегированная лента:**
- По всему портфелю и вотчлисту — всё важное в одном месте
- Приоритет: High Impact новости наверху
- Фильтр по источнику: Reuters / Yahoo / MarketWatch / Reddit / StockTwits
- Фильтр по влиянию: Low / Medium / High impact
- Фильтр по sentiment: Positive / Neutral / Negative

**Sentiment Analytics:**
- Sentiment-тренд за 7 дней — line chart, как менялся информационный фон по акции
- Средний sentiment score за период
- Количество новостей в день (bar chart)

**Метки на графике:**
- Значки в точках выхода важных публикаций (кликабельные)
- High impact — крупный значок, Low impact — мелкий
- При hover — заголовок + sentiment

**Social Sentiment (расширение):**
- Упоминания на Reddit (r/investing, r/stocks, r/wallstreetbets)
- StockTwits sentiment
- Buzz score: насколько активно обсуждается акция
- Сравнение social vs news sentiment

### 3.9. Earnings Calendar

**Таблица ближайших отчётов:**
- Фильтр: акции из портфеля / вотчлиста / все S&P 500
- Дата отчёта, тикер, название компании
- Consensus EPS прогноз аналитиков
- Предыдущий фактический EPS
- Whisper number (если доступно)
- Countdown: «через 3 дня», «завтра», «сегодня после закрытия»

**После выхода отчёта:**
- Beat 🟢 / Miss 🔴 / In-line 🟡
- EPS actual vs consensus: отклонение в $ и %
- Revenue actual vs consensus
- Реакция акции: изменение after-hours / на следующий день
- Historical earnings track record: сколько раз подряд beat/miss

**Уведомления:**
- Push за 1 день до отчёта по акциям из портфеля/вотчлиста
- Push сразу после выхода результатов (Beat/Miss)

### 3.10. Insider Transactions

**Таблица транзакций:**
- Дата, имя инсайдера, должность (CEO, CFO, Director и т.д.)
- Тип: Purchase 🟢 / Sale 🔴 / Option Exercise 🟡
- Количество акций, цена, общая сумма
- Доля от их общего пакета акций (контекст: продал 2% vs продал 90%)

**Визуализация на графике:**
- Зелёные метки (покупки) и красные метки (продажи) на candlestick chart
- Размер метки пропорционален объёму сделки

**Аналитика:**
- Кластеры инсайдерских покупок — несколько инсайдеров покупают в одно время → исторически сильный бычий сигнал
- Net insider sentiment за 30/90 дней
- Сравнение insider activity с динамикой акции

---

## 4. Уровни доступа (Free / Auth / Pro / Premium)

### Без авторизации (Public / Landing)

Цель: показать ценность платформы, вовлечь в регистрацию.

| Функция | Доступ |
|---|---|
| Landing page с описанием и живыми демо | ✅ Полный |
| Каталог S&P 500 — таблица с ценами, изменениями, sparklines | ✅ Полный |
| Страница тикера — базовый график (line chart, не candlestick) | ✅ Ограничено |
| Company Profile — описание, сектор, капитализация | ✅ Полный |
| Top Picks — показать топ-3 с блюром остальных | ✅ Тизер |
| AI-прогноз — 1 бесплатный прогноз с watermark «Sign up for more» | ✅ Тизер |
| Новостная лента — последние 5 новостей без sentiment | ✅ Ограничено |
| Earnings Calendar — ближайшие 5 отчётов | ✅ Ограничено |

### Free (после регистрации)

| Функция | Лимит |
|---|---|
| Каталог S&P 500 полный | ✅ |
| Candlestick графики с базовыми индикаторами (SMA, Volume) | ✅ |
| AI-прогноз | 1 прогноз/день, 10 тикеров |
| Top Picks | Топ-5 |
| Портфель | 1 портфель, до 10 позиций |
| Watchlist | 1 вотчлист, до 10 тикеров |
| Новости | Лента с sentiment, без фильтров |
| Earnings Calendar | Полный |
| Insider Transactions | Последние 10 записей |
| Финансовые показатели | Базовые (P/E, Market Cap, EPS) |
| Отчётность SEC | ❌ |
| Аналитика портфеля | Только P&L, без корреляций и секторов |

### Pro ($15/мес)

| Функция | Лимит |
|---|---|
| Всё из Free + | |
| AI-прогноз | 10 прогнозов/день, все 318 активных тикеров |
| Top Picks | Топ-20 |
| Портфель | 5 портфелей, безлимит позиций |
| Watchlist | 5 вотчлистов, безлимит |
| Все индикаторы (RSI, MACD, Bollinger, EMA) | ✅ |
| Новости | Полные фильтры, High Impact алерты |
| Sentiment тренды | ✅ |
| Social Sentiment (Reddit, StockTwits) | ✅ |
| Финансовые показатели | Полные |
| Отчётность SEC | ✅ |
| Аналитика портфеля | Полная (корреляции, секторы, vs S&P 500) |
| Дивидендный календарь | ✅ |
| Confident Signals Dashboard | ✅ |
| Push-уведомления | ✅ |
| Drawing tools на графике | ✅ |

### Premium ($39/мес)

| Функция | Лимит |
|---|---|
| Всё из Pro + | |
| AI-прогноз | Безлимит |
| История прогнозов с точностью | ✅ |
| Backtesting стратегий | ✅ |
| API доступ (REST) | ✅ |
| Экспорт в CSV/Excel/PDF | ✅ |
| Webhook-уведомления | ✅ |
| Priority inference (выделенный GPU) | ✅ |
| Custom alerts (сложные условия) | ✅ |

---

## 5. Landing Page (Public Homepage)

### Концепция

Тёмная тема (dark mode по умолчанию, как Bloomberg/TradingView). Минимализм + wow-эффект через micro-interactions. Цель: за 30 секунд донести — «это Bloomberg для обычных людей, но с AI».

### Структура Landing Page

**Hero Section:**
- Заголовок: крупный gradient-текст «AI-Powered Stock Predictions» с typing animation
- Подзаголовок: «107 data signals. 400 S&P 500 stocks. One prediction engine.»
- CTA: «Try Free Forecast →» (ведёт на демо-прогноз без регистрации)
- Фон: live candlestick chart с плавно дорисовывающейся прогнозной линией (анимация на loop)
- Floating badges: «63% Win Rate» (ensemble ConfLong), «Top-20 Sharpe 1.45» — появляются с fade-in

**Live Demo Window:**
- Встроенный интерактивный мини-дашборд прямо на лендинге
- Поле выбора тикера (AAPL, TSLA, NVDA — 3-5 популярных для демо)
- Нажимаешь «Predict» → анимация загрузки → реальный (или кэшированный) прогноз с графиком
- Под графиком: карточка «What influenced this» с waterfall chart
- Watermark: «Sign up for full access»

**Features Carousel / Bento Grid:**
- Блок из 6-8 карточек в формате bento grid (как Apple.com)
- Каждая карточка: название фичи + мини-скриншот/анимация
  - «AI Forecast» — анимация дорисовки прогноза на графике
  - «Top Picks» — карусель акций с badges
  - «Portfolio Analytics» — donut chart + correlation matrix
  - «News Sentiment» — лента с зелёными/красными метками
  - «Earnings Calendar» — таблица с countdown таймерами
  - «Insider Tracking» — graph с зелёными/красными точками

**How It Works — 3 шага:**
- Animated timeline/stepper
- Step 1: «We collect 107 signals» — иконки модальностей (📈 Technical, 📰 News, 📊 Financials, 🏛️ Macro)
- Step 2: «TFT model processes everything» — анимация нейросети (абстрактная, без деталей)
- Step 3: «You get actionable predictions» — пример signal card BUY + HIGH

**Model Performance Section:**
- Крупные animated counters (count-up при скролле):
  - «63% Win Rate on Consensus BUY signals»
  - «Top-20 Return: +19.2% vs S&P 500 +7.7%»
  - «3-4x Better Than Naive Baseline»
  - «80% Confidence Interval Accuracy: 79%»
- График: Top-20 Strategy vs S&P 500 buy-and-hold (анимированный line chart)
- Disclaimer мелким шрифтом: «Past performance does not guarantee future results»

**Pricing Section:**
- 3 карточки (Free / Pro / Premium) с hover-эффектом
- Toggle: Monthly / Annual (скидка 20%)
- Popular badge на Pro
- CTA «Start Free»

**Testimonials / Social Proof (будущее):**
- Пока заглушка: «Join 1,000+ investors» (counter)
- Место для будущих отзывов

**Footer:**
- Links: About, Docs, API, Blog, Contact
- Legal: Disclaimer, Privacy, Terms
- Social: Twitter/X, GitHub, Discord

### Адаптивность

- Desktop: полноценный layout с bento grid
- Tablet: 2 колонки
- Mobile: single column, упрощённые анимации (performance)

---

## 6. UI/UX — Дизайн-система и Wow-эффект

### Проблема: как избежать «типичного AI-интерфейса»

Типичный AI-UI — это белый фон, rounded cards, синий accent, Geist/Inter шрифт, нулевая индивидуальность. Чтобы PredictaMarket выглядел как продукт, а не как ChatGPT-генерация:

### Визуальная идентичность

**Цветовая палитра:**
- Primary background: `#0A0A0F` (почти чёрный с синим undertone)
- Card/surface: `#12121A` с `border: 1px solid rgba(255,255,255,0.06)`
- Accent primary: gradient `#00D4AA → #00A3FF` (teal-to-blue) — для CTA, прогнозных линий, активных элементов
- Accent success: `#00FF88` (яркий зелёный для BUY/profit)
- Accent danger: `#FF3366` (яркий розово-красный для SELL/loss)
- Accent warning: `#FFB800` (янтарный для HOLD/neutral)
- Text primary: `#E8E8ED`
- Text secondary: `#6B6B80`

**Типографика:**
- Headlines: `Space Grotesk` (geometric, modern, не банальный Inter)
- Body: `DM Sans` или `Plus Jakarta Sans`
- Mono (цифры, тикеры, цены): `JetBrains Mono` или `IBM Plex Mono`
- Размеры: fluid typography с clamp()

**Принципы:**
- Data density как у Bloomberg, UX как у Linear/Vercel
- Много whitespace между секциями, но плотная подача данных внутри карточек
- Glassmorphism для модальных окон и overlay: `backdrop-filter: blur(20px)`
- Subtle gradients на фоне (mesh gradient, едва заметный)
- Иконки: Lucide (линейные, тонкие)

### Анимации и переходы (Framer Motion)

**Принцип: анимация должна нести смысл, а не быть декорацией.**

**Переходы между страницами:**
- Shared layout animation (Framer Motion `layoutId`) — тикер-карточка из списка «разворачивается» в полную страницу
- Page transitions: fade + slight slide (200-300ms, ease-out)

**Micro-interactions:**
- Hover на карточку акции: subtle scale(1.02) + glow border (box-shadow с accent color)
- Signal badges (BUY/SELL) — pulse animation при первом появлении
- Цены: number morphing animation (цифры плавно переходят из старого значения в новое, а не просто заменяются)
- Sparklines: draw animation при появлении в viewport (SVG stroke-dashoffset)
- Loading states: skeleton screens с shimmer (gradient wave)

**Графики:**
- Прогнозная линия: draw animation слева направо (как будто рисуется в реальном времени)
- CI интервалы: fade-in после отрисовки линии
- Метки на графике: pop-in с spring physics (bounce)
- Переключение таймфрейма: morph animation (данные плавно перестраиваются, а не мгновенно заменяются)

**Scroll-triggered:**
- Секции лендинга: stagger animation (элементы появляются один за другим с задержкой 50ms)
- Counters: count-up animation при попадании в viewport
- Графики: animate on scroll (IntersectionObserver)

**Специальные эффекты:**
- «Build Forecast» кнопка: gradient border animation (цвет перетекает по периметру)
- Progress bar при inference: stepped animation с текстом этапов
- Confetti или particle burst при первом успешном прогнозе (onboarding moment)
- Background: subtle floating particles (three.js или CSS, очень лёгкие, не отвлекающие)

### Конкретные библиотеки и технологии

| Задача | Библиотека | Зачем именно она |
|---|---|---|
| Анимации UI | Framer Motion 11+ | LayoutId, AnimatePresence, spring physics — самый мощный для React |
| Графики цен | TradingView Lightweight Charts | Профессиональный candlestick, бесплатный, кастомизируемый |
| Графики аналитики | Recharts или Nivo | Donut, heatmap, waterfall, line — с анимациями |
| Числовые анимации | CountUp.js или custom | Count-up для метрик лендинга |
| Scroll-анимации | Framer Motion `useInView` + `useScroll` | Нативная интеграция с FM |
| Иконки | Lucide React | Легковесные, современные, консистентные |
| Toasts/уведомления | Sonner | Красивые, минималистичные, анимированные |
| Таблицы | TanStack Table v8 | Сортировка, фильтрация, виртуализация |
| Date picker | React Day Picker | Lightweight, кастомизируемый |
| Autocomplete | Downshift / cmdk | Для поиска тикеров |
| 3D фон (опционально) | Three.js / React Three Fiber | Subtle particle background на лендинге |

### Дизайн-референсы

Вместо копирования — собрать лучшее из каждого:
- **Linear.app** — transitions, micro-interactions, dark theme, polish
- **Vercel Dashboard** — data density + clean UI, dark theme
- **Arc Browser** — необычные анимации, spring physics, playful
- **Bloomberg Terminal** — data density (но с современным UX)
- **Robinhood** — простота восприятия финансовых данных
- **Stripe Dashboard** — layout, typography hierarchy
- **Raycast** — command palette (для быстрого поиска тикера: Cmd+K)

### Быстрый поиск (Command Palette)

- Cmd+K / Ctrl+K — открывает поисковую строку поверх всего
- Поиск тикера по названию или символу с autocomplete
- Быстрые действия: «Add to watchlist», «Build forecast», «View earnings»
- Fuzzy search с подсветкой совпадений

---

## 7. Карта экранов (Sitemap)

```
/ (Landing Page) — public
├── /dashboard — auth required
│   ├── Overview (Top Movers, Signals, Market Summary)
│   ├── Top Picks
│   └── Confident Signals
├── /stocks — public (ограничено)
│   ├── /stocks (каталог S&P 500)
│   └── /stocks/[ticker] (страница тикера)
│       ├── Chart (tab)
│       ├── Forecast (tab)
│       ├── Financials (tab)
│       ├── News (tab)
│       ├── Earnings (tab)
│       └── Insiders (tab)
├── /portfolio — auth required
│   ├── /portfolio (список портфелей)
│   └── /portfolio/[id] (конкретный портфель)
│       ├── Holdings
│       ├── Analytics (sectors, correlations, vs S&P)
│       ├── Dividends
│       └── Transactions
├── /watchlist — auth required
├── /news — auth required (полная лента)
├── /earnings — public (ограничено) / auth (полный)
├── /settings — auth required
│   ├── Profile
│   ├── Subscription
│   └── Notifications
├── /auth
│   ├── /login
│   ├── /register
│   └── /forgot-password
└── /api-docs — Premium only
```

---

## 8. Системная архитектура

### Микросервисы

| Сервис | Порт | Ответственность |
|---|---|---|
| api-gateway | 8000 | Единая точка входа, роутинг, JWT-валидация, rate limiting, CORS |
| auth-service | 8001 | Регистрация, логин, JWT-токены, OAuth (Google), роли, подписки |
| market-data-service | 8002 | Получение котировок (yfinance), хранение OHLCV, финансовые метрики |
| news-service | 8003 | RSS-парсинг новостей, FinBERT sentiment analysis, social sentiment |
| forecast-service | 8004 | Загрузка TFT модели, inference, хранение прогнозов, variable importance |
| portfolio-service | 8005 | Портфели пользователей, watchlist, P&L, аналитика, экспорт |
| notification-service | 8006 | Push-уведомления, email алерты, earnings reminders, price alerts |
| edgar-service | 8007 | Загрузка и парсинг SEC EDGAR отчётов (10-Q, 10-K) |
| frontend | 3000 | Next.js 14 SPA |

### Схема взаимодействия

```
Пользователь → Nginx (API Gateway) → микросервис → PostgreSQL / Redis

news-service → Redis Pub/Sub (news.high_impact) → notification-service →
  forecast-service → Redis (forecast.updated) → WebSocket → фронтенд

Airflow DAGs оркестрируют фоновые задачи

WebSocket (Socket.IO):
  - Обновления цен в реальном времени
  - Пуш-уведомления (earnings, alerts, forecast ready)
  - Live sentiment updates
```

---

## 9. Технологический стек

| Слой | Технология | Назначение |
|---|---|---|
| Backend | Python 3.11 + FastAPI | REST API |
| WebSocket | Socket.IO (python-socketio) | Real-time updates |
| База данных | PostgreSQL 15 | Основное хранилище |
| Кэш / брокер | Redis | Pub/Sub + кэш котировок + rate limiting |
| Оркестрация | Apache Airflow 2.x | DAG: сбор данных, прогнозы, обучение |
| Контейнеры | Docker + Docker Compose | Изоляция сервисов |
| Frontend | Next.js 14 + TypeScript + Tailwind | UI |
| State management | Zustand | Лёгкий, удобный для real-time данных |
| Анимации | Framer Motion 11+ | Переходы, micro-interactions, scroll animations |
| Графики цен | TradingView Lightweight Charts | Candlestick + прогноз overlay |
| Графики аналитики | Recharts / Nivo | Donut, heatmap, waterfall, bar |
| Таблицы | TanStack Table v8 | Виртуализация, сортировка, фильтры |
| Поиск | cmdk | Command palette (Cmd+K) |
| Уведомления | Sonner | Toast notifications |
| Auth | NextAuth.js | JWT + OAuth (Google) |
| ML-фреймворк | PyTorch 2.x + pytorch-forecasting 1.1.1 | TFT модель |
| ML-runtime | Lightning 2.x | Training + inference |
| NLP | FinBERT (HuggingFace) + PCA | Sentiment analysis новостей |

---

## 10. Источники данных (все бесплатные)

| Источник | Данные | Частота |
|---|---|---|
| yfinance | OHLCV котировки, финансовые показатели, earnings, insider trading | Каждые 15 мин |
| RSS (Yahoo, Reuters, MarketWatch) | Новости, заголовки | Каждые 30 мин |
| FRED API | CPI, unemployment, fed_funds_rate, yield_curve_spread, M2 | 1 раз в день |
| SEC EDGAR | 10-Q и 10-K отчёты | 1 раз в день |
| Reddit API (PRAW) | r/investing, r/stocks, r/wallstreetbets — mentions + sentiment | Каждые 30 мин |
| StockTwits API | Social sentiment, buzz | Каждые 30 мин |

---

## 11. База данных PostgreSQL

| Схема | Таблицы | Назначение |
|---|---|---|
| auth | users, refresh_tokens, subscriptions, oauth_accounts | Аккаунты, токены, подписки |
| market | instruments, price_history, financial_metrics, company_profiles | Тикеры, OHLCV, финансовые данные |
| edgar | filings, income_statements, balance_sheets, cash_flows | SEC отчётность |
| news | articles, instrument_sentiment, social_mentions, sentiment_daily | Новости, sentiment, social |
| forecast | forecasts, forecast_points, forecast_factors, model_versions, forecast_history | Прогнозы, факторы, история |
| portfolio | portfolios, portfolio_items, transactions, watchlists, watchlist_items | Портфели, сделки |
| earnings | earnings_calendar, earnings_results, eps_estimates | Отчёты, EPS |
| insider | insider_transactions | Инсайдерские сделки |
| notification | alerts, alert_triggers, notification_log | Уведомления |

---

## 12. Airflow DAGs

| DAG | Расписание | Задача |
|---|---|---|
| dag_fetch_prices | Каждые 15 мин (в торговые часы) | yfinance → PostgreSQL |
| dag_fetch_news | Каждые 30 мин | RSS → FinBERT → PCA → PostgreSQL |
| dag_fetch_social | Каждые 30 мин | Reddit + StockTwits → sentiment → PostgreSQL |
| dag_fetch_financials | 1 раз в день (06:00 ET) | yfinance financials + FRED → PostgreSQL |
| dag_fetch_edgar | 1 раз в день (07:00 ET) | SEC EDGAR 10-Q/10-K → парсинг → PostgreSQL |
| dag_fetch_earnings | 1 раз в день (06:30 ET) | Earnings calendar update → PostgreSQL |
| dag_fetch_insider | 1 раз в день (08:00 ET) | Insider transactions → PostgreSQL |
| dag_run_forecast | Каждый час (в торговые часы) | TFT inference → сохранение прогноза |
| dag_high_impact_forecast | Event-driven (Redis trigger) | Пересчёт прогноза при High Impact новости |
| dag_weekly_retrain | Воскресенье 02:00 | Re-train TFT → обновление checkpoint |
| dag_daily_summary | Каждый день 22:00 ET | Генерация daily digest для email |

---

## 13. Монетизация

| Тариф | Цена | Возможности |
|---|---|---|
| Free | $0 | 10 тикеров, 1 прогноз/день, 1 портфель (10 позиций), базовые индикаторы |
| Pro | $15/мес ($144/год) | Все 346 тикеров, 10 прогнозов/день, 5 портфелей, Top Picks 20, полные фильтры, alerts |
| Premium | $39/мес ($374/год) | Безлимит, Backtesting, API доступ, экспорт, priority inference, webhook alerts |

---

## 14. Текущий статус и план

### Фаза 1: ML Foundation ✅
- [x] EDA HuggingFace датасета (2,638 тикеров, 12 секторов)
- [x] Preprocessing: FinBERT embeddings → PCA 32d, macro, FRED, earnings, insider, calendar
- [x] Обновление данных до Apr 2026 (400 тикеров)
- [x] Обучение TFT (7 эпох сохранены: ep0..ep6)
- [x] Ensemble study: per-surface оптимальные веса (ep5-heavy для Top Picks, ep2-heavy для Alpha Signals)
- [x] Evaluation на single test window (Nov 2025 — Apr 2026, N=9200)
- [x] Live inference pipeline (yfinance + RSS + FinBERT + TFT direct forward pass)
- [x] 95% CI в output модели (квантили q0.02 и q0.98)
- [x] Blocklist для 28 S&P 500 тикеров с post-split data mismatch (36 entries total)
- [x] Radical honesty: live_* targets (shrinked) + backtest_* raw в MODEL_METRICS
- [ ] Walk-forward валидация (NB07) — отложено на retrain
- [ ] Retrain на split-adjusted prices — откроет blocklist и снимет bearish bias

### Фаза 2: Backend MVP ✅ ЗАВЕРШЕНА
- [x] 8 микросервисов FastAPI (api-gateway, auth, market-data, news, forecast, portfolio, notification, edgar)
- [x] PostgreSQL 15 — 9 схем, 33+ таблиц, 121+ индексов, UNIQUE constraints
- [x] Redis 7 — кэш, rate limiting (Lua), pub/sub
- [x] JWT auth + refresh token rotation (SHA256 hashed) + Google OAuth
- [x] TFT inference (direct forward pass, ~5-6 сек, реальные прогнозы)
- [x] FinBERT sentiment из RSS → PCA → DB
- [x] Socket.IO WebSocket (price updates, alerts, forecast ready, news high impact)
- [x] Rate limiting по тарифам (Redis Lua atomic INCR+EXPIRE)
- [x] Docker Compose с healthcheck + resource limits на все 8 сервисов
- [x] Sentry error tracking + Prometheus metrics
- [x] 163 теста (22 unit + 141 integration), все зелёные
- [x] 4 code review + 3 tech debt аудита — все критичные исправлены
- [x] Безопасность: header injection fix, constant-time key comparison, JWT validator, ProxyHeadersMiddleware
- [x] API документация: `docs/BACKEND_API.md` (66 эндпоинтов, все schemas)

**Backend реализует ВСЮ функциональность из Фаз 2 + 4:**
Portfolio, Watchlist, Earnings, Insider, News с sentiment, SEC EDGAR, Push-уведомления — всё уже в backend API.

### Фаза 3: Frontend MVP ✅ ЗАВЕРШЕНА
- [x] Next.js 14 + TypeScript + Tailwind + shadcn/ui дизайн-система
- [x] Landing Page с live demo Top Picks
- [x] Dashboard + каталог 318 активных тикеров
- [x] Страница тикера: TradingView candlestick + forecast overlay + news + earnings + insider
- [x] Top Picks страница (ep5-heavy ensemble)
- [x] Alpha Signals (Premium feed, ep2-heavy ensemble)
- [x] Auth (email/password + Google OAuth, JWT + refresh rotation)
- [x] Command Palette (Cmd+K)
- [x] Portfolio management UI с P&L / корреляциями / секторами
- [x] Watchlist UI с quick «Build Forecast»
- [x] News feed с sentiment и фильтрами
- [x] Earnings Calendar
- [x] Notification center (Socket.IO + price/forecast/news/alert events)
- [x] Plain-English PageGuide на всех 9 страницах
- [x] Extreme-forecast warning chip (|1m return| > 30%)
- [x] Live targets vs back-test caveat tooltips (radical honesty)

### Фаза 4: Polish & Launch 🔄 ТЕКУЩАЯ
- [x] Анимации и micro-interactions (Framer Motion)
- [x] Performance optimization (lazy loading, virtualization — TanStack Table)
- [ ] Mobile responsive аудит
- [ ] Stripe integration (Pro $15 / Premium $39)
- [ ] Walk-forward валидация + retrain на split-adjusted prices
- [ ] Деплой MVP (VPS / Railway / AWS)
- [x] CI/CD (GitHub Actions)
- [x] Docker image publishing

---

## 15. Отказ от ответственности (Legal Disclaimer)

> PredictaMarket предоставляет информацию исключительно в образовательных целях. AI-прогнозы не являются финансовой рекомендацией. Прошлые результаты не гарантируют будущую доходность. Инвестирование в акции сопряжено с риском потери капитала. Перед принятием инвестиционных решений проконсультируйтесь с лицензированным финансовым консультантом.
