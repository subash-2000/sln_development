import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const vendorsApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.VENDORS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.VENDORS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.VENDORS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.VENDORS.UPDATE(id), data)),
};
