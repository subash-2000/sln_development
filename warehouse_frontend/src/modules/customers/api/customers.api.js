import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const customersApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.CUSTOMERS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.CUSTOMERS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.CUSTOMERS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.CUSTOMERS.UPDATE(id), data)),
};
