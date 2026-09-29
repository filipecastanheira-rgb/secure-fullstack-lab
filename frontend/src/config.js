/**
 * Central configuration for the frontend.
 *
 * In development, the Vite dev server (port 5173) proxies /api/* to the
 * FastAPI backend (port 8000) — see vite.config.js.
 *
 * In production, Nginx serves the built assets and proxies /api/* to
 * FastAPI. Either way, the browser always talks to the SAME origin, so the
 * endpoints below are relative and no CORS is involved.
 */

export const API_BASE_URL = ''  // empty = same origin as the page

export const API_ENDPOINTS = {
  assets: `${API_BASE_URL}/api/assets`,
  hello: `${API_BASE_URL}/api/hello`,
}
