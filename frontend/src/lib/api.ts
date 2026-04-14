import axios from "axios"
import { toast } from "sonner"
import type {
  AuthResponse,
  User,
  Instrument,
  InstrumentDetail,
  TickerPrice,
  PriceBar,
  Forecast,
  TopPick,
  Portfolio,
  Position,
  SectorAllocation,
  Transaction,
  Watchlist,
  NewsArticle,
  Alert,
  Notification,
  PaginatedResponse,
  EarningsCalendar,
  EarningsResult,
  InsiderTransaction,
} from "@/types"

// ── Axios instance ───────────────────────────────────

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
})

// ── Request interceptor: attach JWT ──────────────────

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("pm_access_token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// ── Response interceptor: handle errors ──────────────

let isRefreshing = false
let failedQueue: { resolve: (token: string) => void; reject: (err: unknown) => void }[] = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((p) => {
    if (token) p.resolve(token)
    else p.reject(error)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 401 — try refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(api(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem("pm_refresh_token")
        if (!refreshToken) throw new Error("No refresh token")

        const { data } = await axios.post<AuthResponse>(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/refresh`,
          { refresh_token: refreshToken }
        )

        localStorage.setItem("pm_access_token", data.access_token)
        localStorage.setItem("pm_refresh_token", data.refresh_token)

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        processQueue(null, data.access_token)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        localStorage.removeItem("pm_access_token")
        localStorage.removeItem("pm_refresh_token")
        if (typeof window !== "undefined") {
          window.location.href = "/auth/login"
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 403 — tier restriction
    if (error.response?.status === 403) {
      toast.error("This feature requires a Pro plan", {
        action: { label: "Upgrade", onClick: () => window.location.href = "/pricing" },
      })
    }

    // 429 — rate limit
    if (error.response?.status === 429) {
      toast.error("Rate limit exceeded. Try again later.")
    }

    // 500 — server error
    if (error.response?.status === 500) {
      toast.error("Something went wrong. Please try again.")
    }

    // Network error (skip cancelled requests from navigation)
    if (!error.response && error.code !== "ERR_CANCELED") {
      toast.error("Connection lost. Check your internet.")
    }

    return Promise.reject(error)
  }
)

// ── Request types ────────────────────────────────────

interface RegisterRequest {
  email: string
  password: string
  name: string
}

interface LoginRequest {
  email: string
  password: string
}

interface RefreshRequest {
  refresh_token: string
}

interface CreatePortfolioRequest {
  name: string
  description?: string
}

interface AddPositionRequest {
  ticker: string
  quantity: number
  price: number
  notes?: string
}

interface CreateWatchlistRequest {
  name: string
}

interface CreateAlertRequest {
  ticker: string
  alert_type: string
  condition_value: number
}

// ── Auth API ─────────────────────────────────────────

export const authApi = {
  register: (data: RegisterRequest) =>
    api.post<AuthResponse>("/api/auth/register", data),
  login: (data: LoginRequest) =>
    api.post<AuthResponse>("/api/auth/login", data),
  refresh: (data: RefreshRequest) =>
    api.post<AuthResponse>("/api/auth/refresh", data),
  google: (data: { id_token?: string; access_token?: string }) =>
    api.post<AuthResponse>("/api/auth/google", data),
  getMe: () =>
    api.get<User>("/api/auth/me"),
  updateMe: (data: { name: string }) =>
    api.put("/api/auth/me", data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post("/api/auth/change-password", data),
}

// ── Market API ───────────────────────────────────────

export const marketApi = {
  getInstruments: (params?: { page?: number; per_page?: number; sector?: string; search?: string; sort_by?: string; order?: string }) =>
    api.get<PaginatedResponse<Instrument>>("/api/market/instruments", { params }),
  getInstrument: (ticker: string) =>
    api.get<InstrumentDetail>(`/api/market/instruments/${ticker}`),
  getHistory: (ticker: string, params?: { period?: string; interval?: string }) =>
    api.get<PriceBar[]>(`/api/market/instruments/${ticker}/history`, { params }),
  getPrice: (ticker: string) =>
    api.get<TickerPrice>(`/api/market/instruments/${ticker}/price`),
  getFinancials: (ticker: string, params?: { period?: string }) =>
    api.get(`/api/market/instruments/${ticker}/financials`, { params }),
  getEarningsUpcoming: (params?: { days?: number }) =>
    api.get<EarningsCalendar[]>("/api/earnings/upcoming", { params }),
  getEarningsHistory: (ticker: string) =>
    api.get<EarningsResult[]>(`/api/earnings/${ticker}/history`),
  getInsider: (ticker: string, params?: { limit?: number }) =>
    api.get<InsiderTransaction[]>(`/api/insider/${ticker}`, { params }),
}

// ── Forecast API ─────────────────────────────────────

export const forecastApi = {
  getTopPicks: (params?: { limit?: number }) =>
    api.get<TopPick[]>("/api/forecast/top-picks", { params }),
  getSignals: (params?: { signal?: string; confidence?: string }) =>
    api.get("/api/forecast/signals", { params }),
  getForecast: (ticker: string) =>
    api.get<Forecast>(`/api/forecast/${ticker}`),
  createForecast: (ticker: string) =>
    api.post<Forecast>(`/api/forecast/${ticker}`, null, { timeout: 60000 }),
  getForecastHistory: (ticker: string, params?: { limit?: number }) =>
    api.get(`/api/forecast/${ticker}/history`, { params }),
  createBatch: (tickers: string[]) =>
    api.post("/api/forecast/batch", { tickers }),
  getBatchStatus: (jobId: string) =>
    api.get(`/api/forecast/batch/${jobId}`),
}

// ── Portfolio API ────────────────────────────────────

export const portfolioApi = {
  getPortfolios: () =>
    api.get<Portfolio[]>("/api/portfolio/portfolios"),
  createPortfolio: (data: CreatePortfolioRequest) =>
    api.post<Portfolio>("/api/portfolio/portfolios", data),
  getPortfolio: (id: string) =>
    api.get<Portfolio>(`/api/portfolio/portfolios/${id}`),
  deletePortfolio: (id: string) =>
    api.delete(`/api/portfolio/portfolios/${id}`),
  getPositions: (portfolioId: string) =>
    api.get<Position[]>(`/api/portfolio/portfolios/${portfolioId}/positions`),
  addPosition: (portfolioId: string, data: AddPositionRequest) =>
    api.post<Position>(`/api/portfolio/portfolios/${portfolioId}/positions`, data),
  deletePosition: (portfolioId: string, ticker: string, params?: { quantity?: number; price?: number }) =>
    api.delete(`/api/portfolio/portfolios/${portfolioId}/positions/${ticker}`, { params }),
  getAnalytics: (portfolioId: string) =>
    api.get(`/api/portfolio/portfolios/${portfolioId}/analytics`),
  getSectors: (portfolioId: string) =>
    api.get<SectorAllocation[]>(`/api/portfolio/portfolios/${portfolioId}/sectors`),
  getTransactions: (portfolioId: string, params?: { limit?: number }) =>
    api.get<Transaction[]>(`/api/portfolio/portfolios/${portfolioId}/transactions`, { params }),
  exportCSV: (portfolioId: string) =>
    api.get(`/api/portfolio/portfolios/${portfolioId}/export`, { responseType: "blob" }),

  // Watchlists
  getWatchlists: () =>
    api.get<Watchlist[]>("/api/portfolio/watchlists"),
  createWatchlist: (data: CreateWatchlistRequest) =>
    api.post<Watchlist>("/api/portfolio/watchlists", data),
  getWatchlist: (id: string) =>
    api.get<Watchlist>(`/api/portfolio/watchlists/${id}`),
  addWatchlistItem: (id: string, ticker: string) =>
    api.post(`/api/portfolio/watchlists/${id}/items`, { ticker }),
  removeWatchlistItem: (id: string, ticker: string) =>
    api.delete(`/api/portfolio/watchlists/${id}/items/${ticker}`),
}

// ── News API ─────────────────────────────────────────

export const newsApi = {
  getNews: (params?: { ticker?: string; source?: string; sentiment?: string; impact?: string; page?: number; per_page?: number }) =>
    api.get<PaginatedResponse<NewsArticle>>("/api/news/news", { params }),
  getNewsByTicker: (ticker: string, params?: { page?: number; per_page?: number }) =>
    api.get<PaginatedResponse<NewsArticle>>(`/api/news/news/${ticker}`, { params }),
  getTickerSentiment: (ticker: string, params?: { days?: number }) =>
    api.get(`/api/news/news/${ticker}/sentiment`, { params }),
  getFeed: () =>
    api.get<PaginatedResponse<NewsArticle>>("/api/news/feed"),
}

// ── Notification API ─────────────────────────────────

export const notificationApi = {
  getAlerts: (params?: { limit?: number }) =>
    api.get<Alert[]>("/api/notifications/alerts", { params }),
  createAlert: (data: CreateAlertRequest) =>
    api.post<Alert>("/api/notifications/alerts", data),
  deleteAlert: (id: string) =>
    api.delete(`/api/notifications/alerts/${id}`),
  getHistory: (params?: { limit?: number }) =>
    api.get<Notification[]>("/api/notifications/alerts/history", { params }),
}

// ── Edgar API ────────────────────────────────────────

export const edgarApi = {
  getFilings: (ticker: string, params?: { filing_type?: string; limit?: number }) =>
    api.get(`/api/edgar/${ticker}/filings`, { params }),
  getIncome: (ticker: string, params?: { limit?: number }) =>
    api.get(`/api/edgar/${ticker}/income`, { params }),
  getBalance: (ticker: string, params?: { limit?: number }) =>
    api.get(`/api/edgar/${ticker}/balance`, { params }),
  getCashFlow: (ticker: string, params?: { limit?: number }) =>
    api.get(`/api/edgar/${ticker}/cash-flow`, { params }),
}

// ── Billing API ─────────────────────────────────────

export const billingApi = {
  getPlans: () =>
    api.get("/api/billing/plans"),
  createCheckout: (data: { plan: string; billing: string }) =>
    api.post<{ checkout_url: string }>("/api/billing/checkout", data),
  getPortal: () =>
    api.get<{ portal_url: string }>("/api/billing/portal"),
  getSubscription: () =>
    api.get("/api/billing/subscription"),
}

export default api
