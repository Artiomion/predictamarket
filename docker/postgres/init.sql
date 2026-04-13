-- =============================================================================
-- PredictaMarket — PostgreSQL 15 init script
-- 9 schemas, UUID PKs, timestamptz, indexes, FK CASCADE, soft delete
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ======================= SCHEMA: auth ========================================
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE auth.users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name   VARCHAR(255),
    avatar_url  TEXT,
    tier        VARCHAR(20) NOT NULL DEFAULT 'free'
                CHECK (tier IN ('free', 'pro', 'premium')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    last_login  TIMESTAMPTZ,
    deleted_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_auth_users_email ON auth.users (email);
CREATE INDEX idx_auth_users_tier ON auth.users (tier);

CREATE TABLE auth.refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token       VARCHAR(512) NOT NULL UNIQUE,
    device_info VARCHAR(255),
    ip_address  VARCHAR(45),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_auth_refresh_tokens_user ON auth.refresh_tokens (user_id);
CREATE INDEX idx_auth_refresh_tokens_token ON auth.refresh_tokens (token);

CREATE TABLE auth.subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id    VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    tier            VARCHAR(20) NOT NULL DEFAULT 'free'
                    CHECK (tier IN ('free', 'pro', 'premium')),
    status          VARCHAR(30) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_auth_subscriptions_user ON auth.subscriptions (user_id);
CREATE INDEX idx_auth_subscriptions_stripe ON auth.subscriptions (stripe_subscription_id);

CREATE TABLE auth.oauth_accounts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider    VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token  TEXT,
    refresh_token TEXT,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_user_id)
);
CREATE INDEX idx_auth_oauth_user ON auth.oauth_accounts (user_id);

-- ======================= SCHEMA: market ======================================
CREATE SCHEMA IF NOT EXISTS market;

CREATE TABLE market.instruments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker      VARCHAR(10) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    sector      VARCHAR(100),
    industry    VARCHAR(255),
    market_cap  BIGINT,
    exchange    VARCHAR(20) DEFAULT 'NYSE',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_market_instruments_ticker ON market.instruments (ticker);
CREATE INDEX idx_market_instruments_sector ON market.instruments (sector);

CREATE TABLE market.price_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    date            DATE NOT NULL,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION NOT NULL,
    adj_close       DOUBLE PRECISION,
    volume          BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, date)
);
CREATE INDEX idx_market_price_ticker ON market.price_history (ticker);
CREATE INDEX idx_market_price_date ON market.price_history (date);
CREATE INDEX idx_market_price_instrument ON market.price_history (instrument_id);
CREATE INDEX idx_market_price_ticker_date ON market.price_history (ticker, date DESC);

CREATE TABLE market.macro_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date            DATE NOT NULL UNIQUE,
    vix             DOUBLE PRECISION,
    treasury_10y    DOUBLE PRECISION,
    sp500           DOUBLE PRECISION,
    dxy             DOUBLE PRECISION,
    gold            DOUBLE PRECISION,
    oil             DOUBLE PRECISION,
    vix_ma5         DOUBLE PRECISION,
    sp500_return    DOUBLE PRECISION,
    vix_contango    DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_market_macro_date ON market.macro_history (date);

CREATE TABLE market.financial_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    period_end      DATE NOT NULL,
    period_type     VARCHAR(10) NOT NULL CHECK (period_type IN ('quarterly', 'annual')),
    revenue         DOUBLE PRECISION,
    net_income      DOUBLE PRECISION,
    eps             DOUBLE PRECISION,
    pe_ratio        DOUBLE PRECISION,
    pb_ratio        DOUBLE PRECISION,
    dividend_yield  DOUBLE PRECISION,
    debt_to_equity  DOUBLE PRECISION,
    roe             DOUBLE PRECISION,
    roa             DOUBLE PRECISION,
    free_cash_flow  DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    current_ratio   DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, period_end, period_type)
);
CREATE INDEX idx_market_metrics_ticker ON market.financial_metrics (ticker);
CREATE INDEX idx_market_metrics_instrument ON market.financial_metrics (instrument_id);

CREATE TABLE market.company_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE UNIQUE,
    ticker          VARCHAR(10) NOT NULL UNIQUE,
    description     TEXT,
    website         VARCHAR(500),
    logo_url        VARCHAR(500),
    ceo             VARCHAR(255),
    employees       INTEGER,
    headquarters    VARCHAR(255),
    founded_year    INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_market_profiles_ticker ON market.company_profiles (ticker);

-- ======================= SCHEMA: edgar =======================================
CREATE SCHEMA IF NOT EXISTS edgar;

CREATE TABLE edgar.filings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    cik             VARCHAR(20),
    accession_number VARCHAR(30) NOT NULL UNIQUE,
    filing_type     VARCHAR(20) NOT NULL,
    filing_date     DATE NOT NULL,
    period_of_report DATE,
    url             TEXT,
    processed       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_edgar_filings_ticker ON edgar.filings (ticker);
CREATE INDEX idx_edgar_filings_date ON edgar.filings (filing_date);
CREATE INDEX idx_edgar_filings_type ON edgar.filings (filing_type);
CREATE INDEX idx_edgar_filings_instrument ON edgar.filings (instrument_id);

CREATE TABLE edgar.income_statements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filing_id       UUID NOT NULL REFERENCES edgar.filings(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    period_end      DATE NOT NULL,
    revenue         DOUBLE PRECISION,
    cost_of_revenue DOUBLE PRECISION,
    gross_profit    DOUBLE PRECISION,
    operating_income DOUBLE PRECISION,
    net_income      DOUBLE PRECISION,
    eps_basic       DOUBLE PRECISION,
    eps_diluted     DOUBLE PRECISION,
    shares_outstanding BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_edgar_income_ticker ON edgar.income_statements (ticker);
CREATE INDEX idx_edgar_income_filing ON edgar.income_statements (filing_id);

CREATE TABLE edgar.balance_sheets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filing_id       UUID NOT NULL REFERENCES edgar.filings(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    period_end      DATE NOT NULL,
    total_assets    DOUBLE PRECISION,
    total_liabilities DOUBLE PRECISION,
    stockholders_equity DOUBLE PRECISION,
    cash_and_equivalents DOUBLE PRECISION,
    total_debt      DOUBLE PRECISION,
    current_assets  DOUBLE PRECISION,
    current_liabilities DOUBLE PRECISION,
    property_plant_equipment DOUBLE PRECISION,
    retained_earnings DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_edgar_balance_ticker ON edgar.balance_sheets (ticker);
CREATE INDEX idx_edgar_balance_filing ON edgar.balance_sheets (filing_id);

CREATE TABLE edgar.cash_flows (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filing_id       UUID NOT NULL REFERENCES edgar.filings(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    period_end      DATE NOT NULL,
    operating_cash_flow DOUBLE PRECISION,
    investing_cash_flow DOUBLE PRECISION,
    financing_cash_flow DOUBLE PRECISION,
    capital_expenditures DOUBLE PRECISION,
    free_cash_flow  DOUBLE PRECISION,
    dividends_paid  DOUBLE PRECISION,
    stock_repurchases DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_edgar_cashflow_ticker ON edgar.cash_flows (ticker);
CREATE INDEX idx_edgar_cashflow_filing ON edgar.cash_flows (filing_id);

-- ======================= SCHEMA: news ========================================
CREATE SCHEMA IF NOT EXISTS news;

CREATE TABLE news.articles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    source          VARCHAR(100) NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL,
    summary         TEXT,
    content         TEXT,
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20) CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    impact_level    VARCHAR(20) DEFAULT 'low'
                    CHECK (impact_level IN ('low', 'medium', 'high')),
    is_processed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_news_articles_published ON news.articles (published_at DESC);
CREATE INDEX idx_news_articles_source ON news.articles (source);
CREATE INDEX idx_news_articles_impact ON news.articles (impact_level);

CREATE TABLE news.instrument_sentiment (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id      UUID NOT NULL REFERENCES news.articles(id) ON DELETE CASCADE,
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    relevance_score DOUBLE PRECISION DEFAULT 1.0,
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20) CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_news_sentiment_ticker ON news.instrument_sentiment (ticker);
CREATE INDEX idx_news_sentiment_article ON news.instrument_sentiment (article_id);
CREATE INDEX idx_news_sentiment_instrument ON news.instrument_sentiment (instrument_id);

CREATE TABLE news.social_mentions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    platform        VARCHAR(50) NOT NULL CHECK (platform IN ('reddit', 'stocktwits', 'twitter')),
    post_id         VARCHAR(255),
    author          VARCHAR(255),
    content         TEXT,
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20) CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    upvotes         INTEGER DEFAULT 0,
    comments_count  INTEGER DEFAULT 0,
    posted_at       TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_news_social_ticker ON news.social_mentions (ticker);
CREATE INDEX idx_news_social_platform ON news.social_mentions (platform);
CREATE INDEX idx_news_social_posted ON news.social_mentions (posted_at DESC);

CREATE TABLE news.sentiment_daily (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    date            DATE NOT NULL,
    avg_sentiment   DOUBLE PRECISION,
    news_count      INTEGER DEFAULT 0,
    social_count    INTEGER DEFAULT 0,
    positive_count  INTEGER DEFAULT 0,
    negative_count  INTEGER DEFAULT 0,
    neutral_count   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, date)
);
CREATE INDEX idx_news_daily_ticker ON news.sentiment_daily (ticker);
CREATE INDEX idx_news_daily_date ON news.sentiment_daily (date);

-- ======================= SCHEMA: forecast ====================================
CREATE SCHEMA IF NOT EXISTS forecast;

CREATE TABLE forecast.model_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version         VARCHAR(50) NOT NULL UNIQUE,
    checkpoint_path TEXT NOT NULL,
    metrics         JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    trained_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE forecast.forecasts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    model_version_id UUID NOT NULL REFERENCES forecast.model_versions(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    forecast_date   DATE NOT NULL,
    current_close   DOUBLE PRECISION NOT NULL,
    signal          VARCHAR(10) NOT NULL CHECK (signal IN ('BUY', 'SELL', 'HOLD')),
    confidence      VARCHAR(10) NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    predicted_return_1d  DOUBLE PRECISION,
    predicted_return_1w  DOUBLE PRECISION,
    predicted_return_1m  DOUBLE PRECISION,
    inference_time_s     DOUBLE PRECISION,
    is_latest       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_forecast_ticker ON forecast.forecasts (ticker);
CREATE INDEX idx_forecast_date ON forecast.forecasts (forecast_date DESC);
CREATE INDEX idx_forecast_instrument ON forecast.forecasts (instrument_id);
CREATE INDEX idx_forecast_signal ON forecast.forecasts (signal);
CREATE INDEX idx_forecast_latest ON forecast.forecasts (is_latest) WHERE is_latest = TRUE;
CREATE INDEX idx_forecast_ticker_date ON forecast.forecasts (ticker, forecast_date DESC);

CREATE TABLE forecast.forecast_points (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_id     UUID NOT NULL REFERENCES forecast.forecasts(id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    horizon_label   VARCHAR(10),
    median          DOUBLE PRECISION NOT NULL,
    lower_80        DOUBLE PRECISION,
    upper_80        DOUBLE PRECISION,
    lower_95        DOUBLE PRECISION,
    upper_95        DOUBLE PRECISION,
    q_02            DOUBLE PRECISION,
    q_10            DOUBLE PRECISION,
    q_25            DOUBLE PRECISION,
    q_50            DOUBLE PRECISION,
    q_75            DOUBLE PRECISION,
    q_90            DOUBLE PRECISION,
    q_98            DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_forecast_points_forecast ON forecast.forecast_points (forecast_id);

CREATE TABLE forecast.forecast_factors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_id     UUID NOT NULL REFERENCES forecast.forecasts(id) ON DELETE CASCADE,
    factor_name     VARCHAR(100) NOT NULL,
    weight          DOUBLE PRECISION NOT NULL,
    direction       VARCHAR(20) CHECK (direction IN ('bullish', 'bearish', 'neutral')),
    rank            INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_forecast_factors_forecast ON forecast.forecast_factors (forecast_id);

CREATE TABLE forecast.forecast_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    forecast_date   DATE NOT NULL,
    horizon_days    INTEGER NOT NULL,
    predicted_price DOUBLE PRECISION NOT NULL,
    actual_price    DOUBLE PRECISION,
    error_pct       DOUBLE PRECISION,
    signal          VARCHAR(10),
    was_correct     BOOLEAN,
    evaluated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_forecast_history_ticker ON forecast.forecast_history (ticker);
CREATE INDEX idx_forecast_history_date ON forecast.forecast_history (forecast_date);

-- ======================= SCHEMA: portfolio ===================================
CREATE SCHEMA IF NOT EXISTS portfolio;

CREATE TABLE portfolio.portfolios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    total_value     DOUBLE PRECISION DEFAULT 0,
    total_pnl       DOUBLE PRECISION DEFAULT 0,
    total_pnl_pct   DOUBLE PRECISION DEFAULT 0,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_portfolio_user ON portfolio.portfolios (user_id);

CREATE TABLE portfolio.portfolio_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolio.portfolios(id) ON DELETE CASCADE,
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    quantity        DOUBLE PRECISION NOT NULL,
    avg_buy_price   DOUBLE PRECISION NOT NULL,
    current_price   DOUBLE PRECISION,
    pnl             DOUBLE PRECISION DEFAULT 0,
    pnl_pct         DOUBLE PRECISION DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (portfolio_id, ticker)
);
CREATE INDEX idx_portfolio_items_portfolio ON portfolio.portfolio_items (portfolio_id);
CREATE INDEX idx_portfolio_items_ticker ON portfolio.portfolio_items (ticker);

CREATE TABLE portfolio.transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id    UUID NOT NULL REFERENCES portfolio.portfolios(id) ON DELETE CASCADE,
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('buy', 'sell')),
    quantity        DOUBLE PRECISION NOT NULL,
    price           DOUBLE PRECISION NOT NULL,
    total_amount    DOUBLE PRECISION NOT NULL,
    notes           TEXT,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_portfolio_tx_portfolio ON portfolio.transactions (portfolio_id);
CREATE INDEX idx_portfolio_tx_ticker ON portfolio.transactions (ticker);
CREATE INDEX idx_portfolio_tx_date ON portfolio.transactions (executed_at DESC);

CREATE TABLE portfolio.watchlists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL DEFAULT 'My Watchlist',
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_portfolio_watchlist_user ON portfolio.watchlists (user_id);

CREATE TABLE portfolio.watchlist_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    watchlist_id    UUID NOT NULL REFERENCES portfolio.watchlists(id) ON DELETE CASCADE,
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (watchlist_id, ticker)
);
CREATE INDEX idx_portfolio_wl_items_watchlist ON portfolio.watchlist_items (watchlist_id);
CREATE INDEX idx_portfolio_wl_items_ticker ON portfolio.watchlist_items (ticker);

-- ======================= SCHEMA: earnings ====================================
CREATE SCHEMA IF NOT EXISTS earnings;

CREATE TABLE earnings.earnings_calendar (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    report_date     DATE NOT NULL,
    fiscal_quarter  VARCHAR(10),
    fiscal_year     INTEGER,
    time_of_day     VARCHAR(20) CHECK (time_of_day IN ('before_market', 'after_market', 'during_market', 'unknown')),
    eps_estimate    DOUBLE PRECISION,
    revenue_estimate DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, report_date)
);
CREATE INDEX idx_earnings_cal_ticker ON earnings.earnings_calendar (ticker);
CREATE INDEX idx_earnings_cal_date ON earnings.earnings_calendar (report_date);

CREATE TABLE earnings.earnings_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    report_date     DATE NOT NULL,
    fiscal_quarter  VARCHAR(10),
    fiscal_year     INTEGER,
    eps_actual      DOUBLE PRECISION,
    eps_estimate    DOUBLE PRECISION,
    eps_surprise_pct DOUBLE PRECISION,
    revenue_actual  DOUBLE PRECISION,
    revenue_estimate DOUBLE PRECISION,
    revenue_surprise_pct DOUBLE PRECISION,
    beat_estimate   BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_earnings_results_ticker ON earnings.earnings_results (ticker);
CREATE INDEX idx_earnings_results_date ON earnings.earnings_results (report_date);
CREATE INDEX idx_earnings_results_instrument ON earnings.earnings_results (instrument_id);

CREATE TABLE earnings.eps_estimates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    fiscal_quarter  VARCHAR(10),
    fiscal_year     INTEGER,
    analyst_count   INTEGER,
    eps_low         DOUBLE PRECISION,
    eps_high        DOUBLE PRECISION,
    eps_avg         DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_earnings_eps_ticker ON earnings.eps_estimates (ticker);

-- ======================= SCHEMA: insider =====================================
CREATE SCHEMA IF NOT EXISTS insider;

CREATE TABLE insider.insider_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instrument_id   UUID NOT NULL REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10) NOT NULL,
    insider_name    VARCHAR(255) NOT NULL,
    insider_title   VARCHAR(255),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'option_exercise', 'gift')),
    shares          DOUBLE PRECISION NOT NULL,
    price_per_share DOUBLE PRECISION,
    total_value     DOUBLE PRECISION,
    shares_owned_after DOUBLE PRECISION,
    filing_date     DATE NOT NULL,
    transaction_date DATE,
    sec_url         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_insider_ticker ON insider.insider_transactions (ticker);
CREATE INDEX idx_insider_date ON insider.insider_transactions (filing_date DESC);
CREATE INDEX idx_insider_instrument ON insider.insider_transactions (instrument_id);
CREATE INDEX idx_insider_type ON insider.insider_transactions (transaction_type);

-- ======================= SCHEMA: notification ================================
CREATE SCHEMA IF NOT EXISTS notification;

CREATE TABLE notification.alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    instrument_id   UUID REFERENCES market.instruments(id) ON DELETE CASCADE,
    ticker          VARCHAR(10),
    alert_type      VARCHAR(50) NOT NULL
                    CHECK (alert_type IN ('price_above', 'price_below', 'signal_change', 'earnings', 'insider', 'news_high_impact', 'forecast_update')),
    condition_value DOUBLE PRECISION,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_triggered    BOOLEAN NOT NULL DEFAULT FALSE,
    triggered_at    TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notification_alerts_user ON notification.alerts (user_id);
CREATE INDEX idx_notification_alerts_ticker ON notification.alerts (ticker);
CREATE INDEX idx_notification_alerts_active ON notification.alerts (is_active) WHERE is_active = TRUE;

CREATE TABLE notification.alert_triggers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id        UUID NOT NULL REFERENCES notification.alerts(id) ON DELETE CASCADE,
    triggered_value DOUBLE PRECISION,
    message         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notification_triggers_alert ON notification.alert_triggers (alert_id);

CREATE TABLE notification.notification_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    alert_id        UUID REFERENCES notification.alerts(id) ON DELETE SET NULL,
    channel         VARCHAR(20) NOT NULL CHECK (channel IN ('in_app', 'email', 'push', 'webhook')),
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notification_log_user ON notification.notification_log (user_id);
CREATE INDEX idx_notification_log_read ON notification.notification_log (user_id, is_read);
CREATE INDEX idx_notification_log_created ON notification.notification_log (created_at DESC);

-- ======================= updated_at trigger ===================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
DO $$
DECLARE
    tbl RECORD;
BEGIN
    FOR tbl IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('auth', 'market', 'edgar', 'news', 'forecast', 'portfolio', 'earnings', 'insider', 'notification')
    LOOP
        EXECUTE format(
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I.%I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            tbl.schemaname, tbl.tablename
        );
    END LOOP;
END;
$$;

-- ======================= Composite partial index for price poller (CR-6) =====
CREATE INDEX IF NOT EXISTS idx_alerts_ticker_active_triggered
ON notification.alerts (ticker, is_active, is_triggered)
WHERE is_active = TRUE AND is_triggered = FALSE AND deleted_at IS NULL;

-- ======================= Additional constraints (TD-6) =======================
ALTER TABLE earnings.earnings_results ADD CONSTRAINT uq_earnings_results_ticker_date UNIQUE (ticker, report_date);
ALTER TABLE edgar.income_statements ADD CONSTRAINT uq_income_stmt_ticker_period UNIQUE (ticker, period_end);
ALTER TABLE edgar.balance_sheets ADD CONSTRAINT uq_balance_sheet_ticker_period UNIQUE (ticker, period_end);
ALTER TABLE edgar.cash_flows ADD CONSTRAINT uq_cash_flow_ticker_period UNIQUE (ticker, period_end);
ALTER TABLE news.social_mentions ADD CONSTRAINT uq_social_platform_post UNIQUE (platform, post_id);

-- ======================= Additional indexes (TD-8) ===========================
CREATE INDEX IF NOT EXISTS idx_income_stmt_period_end ON edgar.income_statements (period_end DESC);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_period_end ON edgar.balance_sheets (period_end DESC);
CREATE INDEX IF NOT EXISTS idx_cash_flow_period_end ON edgar.cash_flows (period_end DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_history_ticker_date ON forecast.forecast_history (ticker, forecast_date DESC);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_period ON market.financial_metrics (period_end, period_type);

-- ======================= Grant search_path ===================================
ALTER DATABASE predictamarket SET search_path TO public, auth, market, edgar, news, forecast, portfolio, earnings, insider, notification;
