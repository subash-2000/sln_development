import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const warehousesApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.WAREHOUSES.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.WAREHOUSES.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.WAREHOUSES.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.WAREHOUSES.UPDATE(id), data)),
};
