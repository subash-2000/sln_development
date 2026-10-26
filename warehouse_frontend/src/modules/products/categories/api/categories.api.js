import apiClient from '../../../../services/api/client';
import { ENDPOINTS } from '../../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../../services/api/unwrap';

export const categoriesApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.PRODUCTS.CATEGORIES.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.PRODUCTS.CATEGORIES.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.PRODUCTS.CATEGORIES.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.PRODUCTS.CATEGORIES.UPDATE(id), data)),
};
