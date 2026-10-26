import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { unwrapData } from '../api/unwrap';

export const authService = {
  login: async (credentials) => {
    const envelope = await apiClient.post(ENDPOINTS.AUTH.LOGIN, {
      username_or_email: credentials.username_or_email || credentials.username,
      password: credentials.password,
    });
    return unwrapData(envelope);
  },

  refreshToken: async (refreshToken) => {
    const envelope = await apiClient.post(ENDPOINTS.AUTH.REFRESH, {
      refresh_token: refreshToken,
    });
    return unwrapData(envelope);
  },

  getCurrentUser: async () => {
    const envelope = await apiClient.get(ENDPOINTS.AUTH.ME);
    return unwrapData(envelope);
  },

  logout: async () => Promise.resolve(),
};
