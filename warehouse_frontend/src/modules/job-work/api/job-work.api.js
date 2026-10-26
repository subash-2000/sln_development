import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const jobWorkApi = {
  list: async (params = {}) => {
    const query = buildListParams(params);
    if (params.dcs_only) {
      query.dcs_only = true;
    }
    return unwrapList(await apiClient.get(ENDPOINTS.JOB_WORK.ORDERS, { params: query }));
  },
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.JOB_WORK.ORDER(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.JOB_WORK.ORDERS, data)),
  issueMaterials: async (id, data) =>
    unwrapData(await apiClient.post(ENDPOINTS.JOB_WORK.ISSUE(id), data)),
};
