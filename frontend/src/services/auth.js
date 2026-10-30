import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({ baseURL: API_BASE_URL });

// Adiciona o token em todos os pedidos, se existir
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Client without interceptors, used for the refresh and logout calls so that
// a 401 from those calls cannot start another refresh or a redirect.
const plain = axios.create({ baseURL: API_BASE_URL });

const REFRESH_LOCK = 'auth-refresh';
let refreshInFlight = null;

function endSession() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/';
}

// Runs inside the cross-tab lock. If the stored refresh token is no longer
// the one this tab had when the request failed, another tab already
// refreshed and the new tokens are in localStorage.
async function doRefresh(tokenAtFailure) {
  const current = localStorage.getItem('refresh_token');
  if (!current) throw new Error('No refresh token');
  if (current !== tokenAtFailure) return;
  const response = await plain.post('/api/auth/refresh', { refresh_token: current });
  localStorage.setItem('access_token', response.data.access_token);
  localStorage.setItem('refresh_token', response.data.refresh_token);
}

// One refresh at a time per tab; navigator.locks serialises tabs.
function refreshSession(tokenAtFailure) {
  if (!refreshInFlight) {
    const run = () => doRefresh(tokenAtFailure);
    const locked = navigator.locks ? navigator.locks.request(REFRESH_LOCK, run) : run();
    refreshInFlight = locked.finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

// On a 401, try one refresh and repeat the request once. If that is not
// possible, clear the tokens and go back to the login page.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    const url = config?.url ?? '';
    const isAuthCall = url.includes('/api/auth/login') || url.includes('/api/auth/refresh');
    if (error.response?.status !== 401 || isAuthCall || !config) {
      return Promise.reject(error);
    }
    if (config._retried) {
      endSession();
      return Promise.reject(error);
    }
    config._retried = true;
    try {
      await refreshSession(localStorage.getItem('refresh_token'));
    } catch {
      endSession();
      return Promise.reject(error);
    }
    return api(config);
  }
);

export const authService = {
  async login(email, password) {
    const response = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('access_token', response.data.access_token);
    // Guardamos o refresh token noutro sítio (ou no mesmo localStorage para simplificar)
    localStorage.setItem('refresh_token', response.data.refresh_token);
    return response.data;
  },
  async logout() {
    const refreshToken = localStorage.getItem('refresh_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    if (!refreshToken) return;
    try {
      await plain.post('/api/auth/logout', { refresh_token: refreshToken });
    } catch {
      // The local session has already ended; nothing more to do.
    }
  },
  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  },
  api,
};
