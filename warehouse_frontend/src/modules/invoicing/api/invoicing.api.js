import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapList } from '../../../services/api/unwrap';

export const invoicingApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.INVOICING.LIST, { params: buildListParams(params) })),
};
