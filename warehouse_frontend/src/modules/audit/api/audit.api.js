import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapList } from '../../../services/api/unwrap';

export const auditApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.AUDIT.LIST, { params: buildListParams(params) })),
};
