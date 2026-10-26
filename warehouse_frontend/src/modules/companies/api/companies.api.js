import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const companiesApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.COMPANIES.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.COMPANIES.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.COMPANIES.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.COMPANIES.UPDATE(id), data)),
};
