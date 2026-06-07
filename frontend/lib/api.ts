/**
 * TradeSense — Axios API Client
 * Centralized HTTP client with JWT auth interceptor and 401 redirect.
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000, // 30s — CSV uploads may take time to process
});

// ── Request Interceptor: Attach JWT ────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Handle 401 ──────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── Auth API ──────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/v1/auth/register', data),

  login: (email: string, password: string) => {
    // FastAPI OAuth2PasswordRequestForm requires form-encoded body
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    return api.post('/v1/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
};

// ── Portfolio API ─────────────────────────────────────────────────────────────
export const portfolioApi = {
  list: () => api.get('/v1/portfolios/'),

  create: (name: string, brokerName?: string) =>
    api.post('/v1/portfolios/', null, {
      params: { name, broker_name: brokerName },
    }),

  uploadCsv: (portfolioId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/v1/uploads/${portfolioId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000, // 2 min for large CSVs + analytics compute
    });
  },

  getHoldings: (portfolioId: string) =>
    api.get(`/v1/portfolios/${portfolioId}/holdings`),
};

// ── Analytics API ─────────────────────────────────────────────────────────────
export const analyticsApi = {
  getSummary: (portfolioId?: string) =>
    api.get('/v1/analytics/behavioral-summary', {
      params: portfolioId ? { portfolio_id: portfolioId } : undefined,
    }),

  getRecommendations: (status: string = 'ACTIVE') =>
    api.get('/v1/analytics/recommendations', { params: { status } }),

  dismissRecommendation: (id: string) =>
    api.patch(`/v1/analytics/recommendations/${id}/dismiss`),
};

// ── System API ────────────────────────────────────────────────────────────────
export const systemApi = {
  health: () => api.get('/health'),
};

export default api;
