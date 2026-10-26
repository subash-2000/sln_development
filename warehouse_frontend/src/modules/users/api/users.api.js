import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const usersApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.USERS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.USERS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.USERS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.USERS.UPDATE(id), data)),
  updateStatus: async (id, status) => unwrapData(await apiClient.patch(ENDPOINTS.USERS.STATUS(id), { status })),
};
