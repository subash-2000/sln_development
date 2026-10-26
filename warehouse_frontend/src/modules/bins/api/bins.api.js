import { locationsApi } from '../../locations/api/locations.api';

export const binsApi = {
  list: async (params) => locationsApi.list({ ...params, storage_type: 'BIN' }),
};
