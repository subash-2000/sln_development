import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const productsApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.PRODUCTS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.PRODUCTS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.PRODUCTS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.PRODUCTS.UPDATE(id), data)),
  categories: {
    list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.PRODUCTS.CATEGORIES.LIST, { params: buildListParams(params) })),
    create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.PRODUCTS.CATEGORIES.CREATE, data)),
  },
  listUoms: async () => unwrapData(await apiClient.get(ENDPOINTS.PRODUCTS.UOMS)),
  listUomCategories: async () => unwrapData(await apiClient.get(ENDPOINTS.PRODUCTS.UOM_CATEGORIES)),
  getUom: async (id) => unwrapData(await apiClient.get(ENDPOINTS.PRODUCTS.UOM_DETAIL(id))),
  createUom: async (data) => unwrapData(await apiClient.post(ENDPOINTS.PRODUCTS.UOM_CREATE, data)),
  updateUom: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.PRODUCTS.UOM_UPDATE(id), data)),
};
