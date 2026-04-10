import type { User, Instrument, Portfolio, Position, NewsArticle, Alert, TopPick } from '@/types';

// ── Auth ──────────────────────────────────────────────
export const mockUser: User = {
  id: 'dbba3ca9-f491-48a9-a9e0-da4b7e0e5cd9',
  email: 'demo@predictamarket.com',
  full_name: 'Demo User',
  avatar_url: null,
  tier: 'free',
  is_active: true,
  is_verified: true,
  created_at: '2026-04-01T00:00:00Z',
};

export const mockToken = 'mock-jwt-token-for-dev';

// ── Market Instruments ────────────────────────────────
export const mockInstruments: Instrument[] = [
  { id: '1', ticker: 'AAPL', name: 'Apple Inc.', sector: 'Technology', industry: 'Consumer Electronics', market_cap: 3798238232576, exchange: 'NMS', is_active: true },
  { id: '2', ticker: 'MSFT', name: 'Microsoft Corporation', sector: 'Technology', industry: 'Software', market_cap: 3200000000000, exchange: 'NMS', is_active: true },
  { id: '3', ticker: 'NVDA', name: 'NVIDIA Corporation', sector: 'Technology', industry: 'Semiconductors', market_cap: 2800000000000, exchange: 'NMS', is_active: true },
  { id: '4', ticker: 'GOOGL', name: 'Alphabet Inc.', sector: 'Communication Services', industry: 'Internet Content', market_cap: 2100000000000, exchange: 'NMS', is_active: true },
  { id: '5', ticker: 'AMZN', name: 'Amazon.com Inc.', sector: 'Consumer Cyclical', industry: 'Internet Retail', market_cap: 2000000000000, exchange: 'NMS', is_active: true },
  { id: '6', ticker: 'JPM', name: 'JPMorgan Chase & Co.', sector: 'Financial Services', industry: 'Banks', market_cap: 680000000000, exchange: 'NYQ', is_active: true },
  { id: '7', ticker: 'LLY', name: 'Eli Lilly and Company', sector: 'Healthcare', industry: 'Drug Manufacturers', market_cap: 750000000000, exchange: 'NYQ', is_active: true },
  { id: '8', ticker: 'CVX', name: 'Chevron Corporation', sector: 'Energy', industry: 'Oil & Gas', market_cap: 382000000000, exchange: 'NYQ', is_active: true },
  { id: '9', ticker: 'COST', name: 'Costco Wholesale', sector: 'Consumer Defensive', industry: 'Discount Stores', market_cap: 449000000000, exchange: 'NMS', is_active: true },
  { id: '10', ticker: 'GE', name: 'GE Aerospace', sector: 'Industrials', industry: 'Aerospace & Defense', market_cap: 325000000000, exchange: 'NYQ', is_active: true },
];

// ── Prices ────────────────────────────────────────────
export const mockPrices: Record<string, { price: number; change: number; change_pct: number }> = {
  AAPL:  { price: 259.49, change: -1.00, change_pct: -0.38 },
  MSFT:  { price: 371.14, change: 3.21,  change_pct: 0.87 },
  NVDA:  { price: 188.85, change: 5.42,  change_pct: 2.95 },
  GOOGL: { price: 161.28, change: -0.54, change_pct: -0.33 },
  AMZN:  { price: 186.42, change: 2.18,  change_pct: 1.18 },
  JPM:   { price: 248.50, change: 1.75,  change_pct: 0.71 },
  LLY:   { price: 941.00, change: -8.50, change_pct: -0.90 },
  CVX:   { price: 187.96, change: -2.30, change_pct: -1.21 },
  COST:  { price: 1012.50, change: 4.20, change_pct: 0.42 },
  GE:    { price: 205.30, change: 1.80,  change_pct: 0.88 },
};

// ── Top Picks ─────────────────────────────────────────
export const mockTopPicks: TopPick[] = [
  { ticker: 'MSFT', name: 'Microsoft Corporation', current_close: 371.14, predicted_return_1m: 6.18, signal: 'BUY', confidence: 'MEDIUM' },
  { ticker: 'GE',   name: 'GE Aerospace',          current_close: 205.30, predicted_return_1m: 4.52, signal: 'BUY', confidence: 'MEDIUM' },
  { ticker: 'COST', name: 'Costco Wholesale',       current_close: 1012.50, predicted_return_1m: 3.21, signal: 'BUY', confidence: 'LOW' },
  { ticker: 'AMZN', name: 'Amazon.com Inc.',        current_close: 186.42, predicted_return_1m: 2.85, signal: 'BUY', confidence: 'LOW' },
  { ticker: 'JPM',  name: 'JPMorgan Chase',         current_close: 248.50, predicted_return_1m: 1.92, signal: 'HOLD', confidence: 'LOW' },
];

// ── Signals ───────────────────────────────────────────
export const mockSignals = [
  { ticker: 'MSFT', signal: 'BUY' as const,  confidence: 'MEDIUM' as const, predicted_return_1m: 6.18, current_close: 371.14 },
  { ticker: 'AAPL', signal: 'SELL' as const, confidence: 'MEDIUM' as const, predicted_return_1m: -6.43, current_close: 259.49 },
  { ticker: 'NVDA', signal: 'SELL' as const, confidence: 'HIGH' as const,   predicted_return_1m: -2.56, current_close: 188.85 },
  { ticker: 'GE',   signal: 'BUY' as const,  confidence: 'MEDIUM' as const, predicted_return_1m: 4.52, current_close: 205.30 },
  { ticker: 'GOOGL',signal: 'HOLD' as const, confidence: 'LOW' as const,    predicted_return_1m: 0.85, current_close: 161.28 },
];

// ── News ──────────────────────────────────────────────
export const mockNews: NewsArticle[] = [
  {
    id: '1',
    title: "Nvidia's stock extends its hot streak — and that's great news for the S&P 500",
    url: 'https://example.com/1',
    source: 'MarketWatch',
    published_at: '2026-04-10T13:23:00Z',
    summary: 'Nvidia shares are up for the eighth session in a row.',
    sentiment_score: 0.89,
    sentiment: 'positive',
    impact: 'high',
    tickers: ['NVDA'],
  },
  {
    id: '2',
    title: "There's a simple reason for the stock market's huge relief rally",
    url: 'https://example.com/2',
    source: 'MarketWatch',
    published_at: '2026-04-08T12:51:00Z',
    summary: 'A huge relief rally was underway following a cease-fire deal.',
    sentiment_score: 0.55,
    sentiment: 'positive',
    impact: 'medium',
    tickers: [],
  },
  {
    id: '3',
    title: 'Oil and fertilizer stocks get pummeled',
    url: 'https://example.com/4',
    source: 'MarketWatch',
    published_at: '2026-04-08T12:33:00Z',
    summary: 'S&P 500 biggest decliners are oil and gas companies.',
    sentiment_score: 0.51,
    sentiment: 'negative',
    impact: 'medium',
    tickers: ['CVX'],
  },
];

// ── Earnings ──────────────────────────────────────────
export const mockUpcomingEarnings = [
  { ticker: 'MSFT', name: 'Microsoft',    report_date: '2026-04-22', eps_estimate: 3.22 },
  { ticker: 'AAPL', name: 'Apple Inc.',    report_date: '2026-04-30', eps_estimate: 1.65 },
  { ticker: 'AMZN', name: 'Amazon.com',    report_date: '2026-05-01', eps_estimate: 1.38 },
];

// ── Portfolio ─────────────────────────────────────────
export const mockPortfolios: Portfolio[] = [
  {
    id: '1f28688c-5d2d-4a13-bc98-74ce3f47e8df',
    name: 'My Tech Portfolio',
    description: 'Top tech picks',
    is_default: true,
    total_value: 15420.50,
    total_pnl: 920.50,
    total_pnl_pct: 6.35,
    created_at: '2026-04-01T00:00:00Z',
  },
];

export const mockPositions: Position[] = [
  { id: '1', ticker: 'AAPL', quantity: 10, avg_buy_price: 250.00, current_price: 259.49, pnl: 94.90, pnl_pct: 3.80 },
  { id: '2', ticker: 'MSFT', quantity: 5,  avg_buy_price: 360.00, current_price: 371.14, pnl: 55.70, pnl_pct: 3.09 },
  { id: '3', ticker: 'NVDA', quantity: 20, avg_buy_price: 180.00, current_price: 188.85, pnl: 177.00, pnl_pct: 4.92 },
];

// ── Watchlist ─────────────────────────────────────────
export const mockWatchlists = [
  {
    id: 'wl-1',
    name: 'My Watchlist',
    items: [
      { ticker: 'AAPL', added_at: '2026-04-05T10:00:00Z' },
      { ticker: 'NVDA', added_at: '2026-04-06T14:00:00Z' },
      { ticker: 'AMZN', added_at: '2026-04-07T09:00:00Z' },
    ],
  },
];

// ── Alerts ────────────────────────────────────────────
export const mockAlerts: Alert[] = [
  { id: '1', ticker: 'AAPL', alert_type: 'price_above', condition_value: 270, is_active: true, is_triggered: false, created_at: '2026-04-10T18:34:08Z' },
  { id: '2', ticker: 'NVDA', alert_type: 'price_below', condition_value: 180, is_active: true, is_triggered: false, created_at: '2026-04-09T10:00:00Z' },
];

// ── Landing Page Stats ────────────────────────────────
export const mockLandingStats = {
  tickers_count: 94,
  model_accuracy: 99.5,
  avg_return: 77.7,
  total_forecasts: 12847,
};
