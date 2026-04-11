// ── Auth ──────────────────────────────────────────────

export type Tier = 'free' | 'pro' | 'premium';

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  tier: Tier;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  is_new_user: boolean;
}

// ── Market ────────────────────────────────────────────

export interface Instrument {
  id: string;
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  exchange: string;
  is_active: boolean;
}

export interface InstrumentDetail extends Instrument {
  description: string;
  website: string;
  logo_url: string | null;
  ceo: string;
  employees: number;
  headquarters: string;
  founded_year: number;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickerPrice {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  updated_at: string;
}

// ── Forecast ──────────────────────────────────────────

export type Signal = 'BUY' | 'SELL' | 'HOLD';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';
export type ForecastHorizon = '1d' | '3d' | '1w' | '2w' | '1m';

export interface ForecastPoint {
  median: number;
  lower_80: number;
  upper_80: number;
  lower_95: number;
  upper_95: number;
}

export interface ForecastFactor {
  name: string;
  weight: number;
  direction: 'bullish' | 'bearish';
  is_estimated: boolean;
}

export interface Forecast {
  ticker: string;
  current_close: number;
  signal: Signal;
  confidence: Confidence;
  forecast: Record<ForecastHorizon, ForecastPoint>;
  full_curve: number[];
  variable_importance: {
    top_factors: ForecastFactor[];
  };
  inference_time_s: number;
  forecast_date: string;
  predicted_return_1d: number;
  predicted_return_1w: number;
  predicted_return_1m: number;
  news_articles_used: number;
  persisted: boolean;
}

export interface TopPick {
  ticker: string;
  name: string;
  current_close: number;
  predicted_return_1m: number;
  signal: Signal;
  confidence: Confidence;
}

// ── Portfolio ─────────────────────────────────────────

export interface Portfolio {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  created_at: string;
}

export interface Position {
  id: string;
  ticker: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

export interface PortfolioAnalytics {
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  positions_count: number;
  best_position: string;
  worst_position: string;
}

export interface SectorAllocation {
  sector: string;
  value: number;
  pct: number;
}

export interface Transaction {
  id: string;
  ticker: string;
  type: 'buy' | 'sell';
  quantity: number;
  price: number;
  total: number;
  created_at: string;
}

// ── Watchlist ─────────────────────────────────────────

export interface WatchlistItem {
  id: string;
  ticker: string;
  added_at: string;
}

export interface Watchlist {
  id: string;
  name: string;
  created_at: string;
  items: WatchlistItem[];
}

// ── News ──────────────────────────────────────────────

export type Sentiment = 'positive' | 'negative' | 'neutral';
export type Impact = 'high' | 'medium' | 'low';

export interface NewsArticle {
  id: string;
  title: string;
  url: string;
  source: string;
  published_at: string;
  tickers: string[];
  sentiment: Sentiment;
  sentiment_score: number;
  impact: Impact;
  summary: string;
}

// ── Earnings ──────────────────────────────────────────

export interface EarningsCalendar {
  ticker: string;
  name: string;
  report_date: string;
  time_of_day: 'before_market' | 'after_market';
  eps_estimate: number | null;
}

export interface EarningsResult {
  ticker: string;
  report_date: string;
  eps_actual: number;
  eps_estimate: number;
  eps_surprise_pct: number;
  revenue_actual: number;
  revenue_estimate: number;
}

// ── Alerts ────────────────────────────────────────────

export type AlertType =
  | 'price_above'
  | 'price_below'
  | 'forecast_change'
  | 'news_high_impact'
  | 'earnings_upcoming';

export interface Alert {
  id: string;
  ticker: string;
  alert_type: AlertType;
  condition_value: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  channel: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

// ── Insider ───────────────────────────────────────────

export interface InsiderTransaction {
  insider_name: string;
  title: string;
  transaction_type: 'buy' | 'sell';
  shares: number;
  price: number;
  total_value: number;
  date: string;
  ticker: string;
}

// ── Landing ───────────────────────────────────────────

export interface LandingStats {
  tickers_count: number;
  model_accuracy: number;
  avg_return: number;
  total_forecasts: number;
}

// ── Pagination ────────────────────────────────────────

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}
