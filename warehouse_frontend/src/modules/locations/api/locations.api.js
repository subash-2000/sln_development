import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const locationsApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.LOCATIONS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.LOCATIONS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.LOCATIONS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.LOCATIONS.UPDATE(id), data)),
};
