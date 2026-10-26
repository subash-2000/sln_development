import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapList } from '../../../services/api/unwrap';

export const vendorStockApi = {
  list: async (params) => unwrapList(await apiClient.get(ENDPOINTS.VENDOR_STOCK.LIST, { params: buildListParams(params) })),
};
