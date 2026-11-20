import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const billingApi = {
  periods: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.PERIODS, { params: buildListParams(params) })),
  documents: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.DOCUMENTS, { params: buildListParams(params) })),
  createPeriod: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.PERIODS, data)),
  calculate: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.CALCULATE, data)),
  document: async (id) => unwrapData(await apiClient.get(ENDPOINTS.BILLING.DOCUMENT(id))),
  confirm: async (id) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.CONFIRM(id))),
  addManualCharge: async (id, data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.MANUAL_CHARGES(id), data)),
  runMonthEnd: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.MONTH_END_RUN, data)),
};
