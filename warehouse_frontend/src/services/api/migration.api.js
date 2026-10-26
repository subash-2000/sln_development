import apiClient from './client';
import { ENDPOINTS } from './endpoints';
import { unwrapData, unwrapList } from './unwrap';

export const migrationApi = {
  import: async (type, file, mapping) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('column_mapping', JSON.stringify(mapping));
    
    const response = await apiClient.post(
      `${ENDPOINTS.MIGRATION.IMPORT}?import_type=${type}`, 
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return unwrapData(response);
  },
  
  downloadTemplate: async (type) => {
    const response = await apiClient.get(
      `${ENDPOINTS.MIGRATION.TEMPLATE}?import_type=${type}`,
      { responseType: 'blob' }
    );
    const blob = response instanceof Blob ? response : new Blob([response?.data ?? response]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${String(type).toLowerCase()}_import_template.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  export: async (type, format = 'excel') => {
    const response = await apiClient.get(
      `${ENDPOINTS.MIGRATION.EXPORT}?export_type=${type}&format=${format}`,
      { responseType: 'blob' }
    );
    
    // Create download link
    const payload = response instanceof Blob ? response : response?.data ?? response;
    const url = window.URL.createObjectURL(payload instanceof Blob ? payload : new Blob([payload]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${type.toLowerCase()}_export_${new Date().getTime()}.${format === 'excel' ? 'xlsx' : 'csv'}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },

  getBatches: async () => unwrapList(await apiClient.get(ENDPOINTS.MIGRATION.BATCHES)),
  getBatchDetail: async (id) => unwrapData(await apiClient.get(ENDPOINTS.MIGRATION.BATCH_DETAIL(id))),
};
