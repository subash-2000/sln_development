import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const creditDebitApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.CREDIT_DEBIT.LIST, { params: buildListParams(params) })),
  summary: async (params) => unwrapData(await apiClient.get(ENDPOINTS.CREDIT_DEBIT.SUMMARY, { params })),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.CREDIT_DEBIT.LIST, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.CREDIT_DEBIT.DETAIL(id), data)),
  confirm: async (id) => unwrapData(await apiClient.post(ENDPOINTS.CREDIT_DEBIT.CONFIRM(id))),
  cancel: async (id, reason) => unwrapData(await apiClient.post(ENDPOINTS.CREDIT_DEBIT.CANCEL(id), { reason })),
};
