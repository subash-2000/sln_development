import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const returnsApi = {
  list: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.RETURNS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.RETURNS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.RETURNS.LIST, data)),
  receive: async (id) => unwrapData(await apiClient.post(ENDPOINTS.RETURNS.RECEIVE(id), {})),
  inspect: async (id, data) => unwrapData(await apiClient.post(ENDPOINTS.RETURNS.INSPECT(id), data)),
  complete: async (id) => unwrapData(await apiClient.post(ENDPOINTS.RETURNS.COMPLETE(id), {})),
  cancel: async (id) => unwrapData(await apiClient.post(ENDPOINTS.RETURNS.CANCEL(id), {})),
};
