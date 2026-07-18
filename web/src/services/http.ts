import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Centralized Axios instance for all calls to the `api` component.
 * Import this instead of calling axios directly so timeouts, headers,
 * and the base URL stay consistent across the app.
 */
export const httpClient = axios.create({
  baseURL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

export default httpClient;
