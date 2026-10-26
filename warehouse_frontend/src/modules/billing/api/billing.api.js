import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapList } from '../../../services/api/unwrap';

export const billingApi = {
  periods: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.PERIODS, { params: buildListParams(params) })),
  documents: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.DOCUMENTS, { params: buildListParams(params) })),
};
