import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const rolesApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.ROLES.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.ROLES.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.ROLES.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.ROLES.UPDATE(id), data)),
  delete: async (id) => unwrapData(await apiClient.delete(ENDPOINTS.ROLES.DELETE(id))),
  permissions: async () => unwrapList(await apiClient.get(ENDPOINTS.PERMISSIONS.LIST)),
};
