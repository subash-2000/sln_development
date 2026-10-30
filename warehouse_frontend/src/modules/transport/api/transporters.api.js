import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

export const transportersApi = {
  list: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.TRANSPORTERS.LIST, { params: buildListParams(params) })),
  getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.TRANSPORTERS.DETAIL(id))),
  create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.TRANSPORTERS.CREATE, data)),
  update: async (id, data) => unwrapData(await apiClient.put(ENDPOINTS.TRANSPORTERS.UPDATE(id), data)),

  // Vehicle sub-master methods
  listAllVehicles: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.TRANSPORTERS.VEHICLES_ALL, { params: buildListParams(params) })),
  listVehicles: async (transporterId, params) =>
    unwrapList(await apiClient.get(ENDPOINTS.TRANSPORTERS.VEHICLES_LIST(transporterId), { params: buildListParams(params) })),
  getVehicleById: async (transporterId, vehicleId) =>
    unwrapData(await apiClient.get(ENDPOINTS.TRANSPORTERS.VEHICLE_DETAIL(transporterId, vehicleId))),
  createVehicle: async (transporterId, data) =>
    unwrapData(await apiClient.post(ENDPOINTS.TRANSPORTERS.VEHICLE_CREATE(transporterId), data)),
  updateVehicle: async (transporterId, vehicleId, data) =>
    unwrapData(await apiClient.put(ENDPOINTS.TRANSPORTERS.VEHICLE_UPDATE(transporterId, vehicleId), data)),
  deleteVehicle: async (transporterId, vehicleId) =>
    unwrapData(await apiClient.delete(ENDPOINTS.TRANSPORTERS.VEHICLE_DELETE(transporterId, vehicleId))),
};
