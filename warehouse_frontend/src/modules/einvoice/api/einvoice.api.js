import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const einvoiceApi = {
  configuration: async () => unwrapData(await apiClient.get(ENDPOINTS.EINVOICE.CONFIGURATION)),
  saveConfiguration: async (payload) => unwrapData(await apiClient.put(ENDPOINTS.EINVOICE.CONFIGURATION, payload)),
  documents: async (params) => unwrapList(await apiClient.get(ENDPOINTS.EINVOICE.DOCUMENTS, { params: buildListParams(params) })),
  createDocument: async (payload) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.DOCUMENTS, payload)),
  generateIrn: async (id) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.GENERATE_IRN(id))),
  cancelIrn: async (id, payload) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.CANCEL_IRN(id), payload)),
  generateEwaybill: async (id) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.GENERATE_EWAYBILL(id))),
  cancelEwaybill: async (id, payload) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.CANCEL_EWAYBILL(id), payload)),
  updateVehicle: async (id, payload) => unwrapData(await apiClient.post(ENDPOINTS.EINVOICE.UPDATE_VEHICLE(id), payload)),
  logs: async (params) => unwrapList(await apiClient.get(ENDPOINTS.EINVOICE.LOGS, { params: buildListParams(params) })),
};
