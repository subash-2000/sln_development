import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { unwrapData } from '../../../services/api/unwrap';

export const dashboardApi = {
  summary: async () => unwrapData(await apiClient.get(ENDPOINTS.DASHBOARD.SUMMARY)),
};
