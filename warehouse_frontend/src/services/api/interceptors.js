import axios from 'axios';
import { normalizeError } from './errors';
import { useAuthStore } from '../../store/auth.store';
import { ENDPOINTS } from './endpoints';

const AUTH_SKIP_REFRESH = [ENDPOINTS.AUTH.LOGIN, ENDPOINTS.AUTH.REFRESH];

const generateUUID = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export const requestInterceptor = (config) => {
  if (!config.headers['X-Request-ID']) {
    config.headers['X-Request-ID'] = generateUUID();
  }

  const { accessToken, companyContext, branchContext } = useAuthStore.getState();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  if (companyContext) {
    config.headers['X-Company-ID'] = companyContext;
  }
  if (branchContext) {
    config.headers['X-Branch-ID'] = branchContext;
  }

  return config;
};

export const responseInterceptor = (response) => response.data;

let refreshPromise = null;

const refreshAccessToken = async (client) => {
  const { refreshToken, setTokens, clearAuth } = useAuthStore.getState();
  if (!refreshToken) {
    clearAuth();
    throw new Error('Session expired');
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        `${client.defaults.baseURL}${ENDPOINTS.AUTH.REFRESH}`,
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      )
      .then((response) => {
        const tokens = response.data?.data;
        if (!tokens?.access_token) {
          throw new Error('Invalid refresh response');
        }
        setTokens(tokens.access_token, tokens.refresh_token);
        return tokens.access_token;
      })
      .catch((error) => {
        clearAuth();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

export const createErrorInterceptor = (client) => async (error) => {
  const originalRequest = error.config;
  const requestUrl = originalRequest?.url || '';
  const shouldSkipRefresh = AUTH_SKIP_REFRESH.some((path) => requestUrl.includes(path));

  if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !shouldSkipRefresh) {
    originalRequest._retry = true;
    try {
      const accessToken = await refreshAccessToken(client);
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return client(originalRequest);
    } catch {
      const normalized = await normalizeError(error);
      return Promise.reject(normalized);
    }
  }

  const normalized = await normalizeError(error);
  return Promise.reject(normalized);
};
