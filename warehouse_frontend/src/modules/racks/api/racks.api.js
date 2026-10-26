import { locationsApi } from '../../locations/api/locations.api';

export const racksApi = {
  list: async (params) => locationsApi.list({ ...params, storage_type: 'RACK' }),
};
