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

// Se der 401, limpa o token e força novo login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/'; // Redireciona para o login (assumindo que está na raiz)
    }
    return Promise.reject(error);
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
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  },
  api,
};
