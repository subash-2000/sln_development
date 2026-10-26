import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const transportersApi = {
  list: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.TRANSPORTERS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.TRANSPORTERS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.TRANSPORTERS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.TRANSPORTERS.UPDATE(id), data)),
};
