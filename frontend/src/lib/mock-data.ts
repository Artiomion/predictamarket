import type { User, Instrument, Forecast, Portfolio, Position, NewsArticle, Alert, TopPick } from '@/types';

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
// ── Forecasts ─────────────────────────────────────────
export const mockForecasts: Record<string, Forecast> = {
  AAPL: {
    ticker: 'AAPL',
    current_close: 259.49,
    signal: 'SELL',
    confidence: 'MEDIUM',
    forecast: {
      '1d': { median: 246.5, lower_80: 235.2, upper_80: 258.1, lower_95: 225.0, upper_95: 268.0 },
      '3d': { median: 245.2, lower_80: 232.0, upper_80: 259.0, lower_95: 220.0, upper_95: 270.0 },
      '1w': { median: 244.3, lower_80: 228.0, upper_80: 261.0, lower_95: 215.0, upper_95: 275.0 },
      '2w': { median: 243.0, lower_80: 224.0, upper_80: 263.0, lower_95: 210.0, upper_95: 280.0 },
      '1m': { median: 242.0, lower_80: 220.0, upper_80: 265.0, lower_95: 200.0, upper_95: 285.0 },
    },
    full_curve: [246.5, 245.8, 245.2, 244.8, 244.3, 243.5, 243.8, 243.2, 242.8, 242.5, 242.3, 242.0, 241.8, 241.5, 241.2, 241.0, 241.5, 241.8, 242.0, 241.5, 241.2, 242.0],
    variable_importance: {
      top_factors: [
        { name: 'Low', weight: 0.0623, direction: 'bearish', is_estimated: false },
        { name: 'oil', weight: 0.0456, direction: 'bearish', is_estimated: false },
        { name: 'eps_surprise_pct', weight: 0.0195, direction: 'bearish', is_estimated: false },
        { name: 'dxy', weight: 0.0127, direction: 'bullish', is_estimated: false },
        { name: 'vix', weight: 0.0098, direction: 'bearish', is_estimated: true },
      ],
    },
    inference_time_s: 5.8,
    forecast_date: '2026-04-10',
    predicted_return_1d: -5.02,
    predicted_return_1w: -6.04,
    predicted_return_1m: -6.43,
    news_articles_used: 3,
    persisted: true,
  },
  MSFT: {
    ticker: 'MSFT',
    current_close: 371.14,
    signal: 'BUY',
    confidence: 'MEDIUM',
    forecast: {
      '1d': { median: 396.0, lower_80: 380.0, upper_80: 412.0, lower_95: 365.0, upper_95: 425.0 },
      '3d': { median: 397.5, lower_80: 378.0, upper_80: 416.0, lower_95: 360.0, upper_95: 430.0 },
      '1w': { median: 398.7, lower_80: 375.0, upper_80: 420.0, lower_95: 358.0, upper_95: 435.0 },
      '2w': { median: 396.5, lower_80: 370.0, upper_80: 425.0, lower_95: 350.0, upper_95: 440.0 },
      '1m': { median: 394.1, lower_80: 360.0, upper_80: 430.0, lower_95: 340.0, upper_95: 450.0 },
    },
    full_curve: [396.0, 397.2, 397.8, 398.1, 398.7, 397.5, 396.8, 396.2, 395.8, 395.5, 395.2, 394.8, 394.5, 394.2, 394.0, 394.3, 394.5, 394.2, 393.8, 393.5, 394.0, 394.1],
    variable_importance: {
      top_factors: [
        { name: 'Volume', weight: 0.0812, direction: 'bullish', is_estimated: false },
        { name: 'sp500', weight: 0.0534, direction: 'bullish', is_estimated: false },
        { name: 'rsi_14', weight: 0.0321, direction: 'bullish', is_estimated: false },
        { name: 'gold', weight: 0.0198, direction: 'bearish', is_estimated: false },
        { name: 'cpi', weight: 0.0087, direction: 'bullish', is_estimated: true },
      ],
    },
    inference_time_s: 0.77,
    forecast_date: '2026-04-10',
    predicted_return_1d: 6.72,
    predicted_return_1w: 7.42,
    predicted_return_1m: 6.18,
    news_articles_used: 5,
    persisted: true,
  },
};

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

// ── Price History (OHLCV for TradingView chart) ──────
export const mockPriceHistory = [
  { date: '2026-03-10', open: 255.0, high: 258.0, low: 253.5, close: 257.2, volume: 38000000 },
  { date: '2026-03-11', open: 257.5, high: 260.1, low: 256.8, close: 259.0, volume: 42000000 },
  { date: '2026-03-12', open: 258.2, high: 259.5, low: 254.0, close: 255.8, volume: 36000000 },
  { date: '2026-03-13', open: 255.0, high: 256.3, low: 249.5, close: 250.1, volume: 45000000 },
  { date: '2026-03-14', open: 251.0, high: 253.8, low: 249.9, close: 252.8, volume: 32000000 },
  { date: '2026-03-17', open: 253.0, high: 255.1, low: 252.2, close: 254.2, volume: 31000000 },
  { date: '2026-03-18', open: 252.6, high: 254.9, low: 249.0, close: 249.9, volume: 35000000 },
  { date: '2026-03-19', open: 249.4, high: 251.8, low: 247.3, close: 249.0, volume: 34000000 },
  { date: '2026-03-20', open: 248.0, high: 249.2, low: 246.0, close: 248.0, volume: 38000000 },
  { date: '2026-03-24', open: 250.4, high: 254.8, low: 249.6, close: 251.6, volume: 45000000 },
  { date: '2026-03-25', open: 254.1, high: 255.0, low: 251.6, close: 252.6, volume: 28000000 },
  { date: '2026-03-26', open: 252.1, high: 257.0, low: 250.8, close: 252.9, volume: 41000000 },
  { date: '2026-03-27', open: 253.9, high: 255.5, low: 248.1, close: 248.8, volume: 47000000 },
  { date: '2026-03-31', open: 247.9, high: 255.5, low: 247.1, close: 253.8, volume: 49000000 },
  { date: '2026-04-01', open: 254.1, high: 256.2, low: 253.3, close: 255.6, volume: 40000000 },
  { date: '2026-04-02', open: 254.2, high: 256.1, low: 250.6, close: 255.9, volume: 31000000 },
  { date: '2026-04-03', open: 256.0, high: 258.5, low: 254.8, close: 257.3, volume: 33000000 },
  { date: '2026-04-04', open: 257.8, high: 259.2, low: 256.5, close: 258.1, volume: 29000000 },
  { date: '2026-04-07', open: 256.2, high: 256.2, low: 245.7, close: 253.5, volume: 62000000 },
  { date: '2026-04-08', open: 258.5, high: 259.8, low: 256.5, close: 258.9, volume: 41000000 },
  { date: '2026-04-09', open: 259.0, high: 261.1, low: 256.1, close: 260.5, volume: 28000000 },
  { date: '2026-04-10', open: 260.0, high: 262.2, low: 259.1, close: 259.5, volume: 12900000 },
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

// ── Insider Transactions ─────────────────────────────
export const mockInsiderTransactions = [
  { insider_name: 'Tim Cook', title: 'CEO', transaction_type: 'sell' as const, shares: 75000, price: 258.50, total_value: 19387500, date: '2026-04-08', ticker: 'AAPL' },
  { insider_name: 'Luca Maestri', title: 'CFO', transaction_type: 'sell' as const, shares: 30000, price: 255.20, total_value: 7656000, date: '2026-03-28', ticker: 'AAPL' },
  { insider_name: 'Jeff Williams', title: 'COO', transaction_type: 'buy' as const, shares: 10000, price: 248.00, total_value: 2480000, date: '2026-03-20', ticker: 'AAPL' },
  { insider_name: 'Deirdre O\'Brien', title: 'SVP Retail', transaction_type: 'sell' as const, shares: 15000, price: 252.80, total_value: 3792000, date: '2026-03-15', ticker: 'AAPL' },
  { insider_name: 'Craig Federighi', title: 'SVP Engineering', transaction_type: 'buy' as const, shares: 5000, price: 250.00, total_value: 1250000, date: '2026-03-10', ticker: 'AAPL' },
];

// ── Landing Page Stats ────────────────────────────────
export const mockLandingStats = {
  tickers_count: 94,
  model_accuracy: 99.5,
  avg_return: 77.7,
  total_forecasts: 12847,
};
