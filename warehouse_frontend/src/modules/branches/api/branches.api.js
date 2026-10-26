import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const branchesApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BRANCHES.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.BRANCHES.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BRANCHES.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.BRANCHES.UPDATE(id), data)),
};
