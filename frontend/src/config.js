/**
 * Central configuration for the frontend.
 *
 * If the backend's host or port changes (e.g. when re-provisioning the lab
 * network), update it HERE — nothing else needs to change.
 */

export const API_BASE_URL = 'http://192.168.1.173:8000'

export const API_ENDPOINTS = {
  assets: `${API_BASE_URL}/api/assets`,
  hello: `${API_BASE_URL}/api/hello`,
}
