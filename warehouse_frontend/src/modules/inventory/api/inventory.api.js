import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

const downloadBlob = (response, fallbackName) => {
  const blob = response.data;
  if (!(blob instanceof Blob) || blob.size < 64) {
    throw new Error('Export file was empty or invalid. Please try again.');
  }
  if (blob.type && blob.type.includes('json')) {
    throw new Error('Export failed on the server. Please try again.');
  }
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const inventoryApi = {
  stock: async (params) => unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.STOCK, { params: buildListParams(params) })),
  exportInventoryMaster: async (supplier = 'ALL') => {
    try {
      const response = await apiClient.get(ENDPOINTS.INVENTORY.STOCK_EXPORT_INVENTORY_MASTER, {
        params: { supplier },
        responseType: 'blob',
      });
      const ext = supplier === 'ALL' ? 'zip' : 'xlsx';
      downloadBlob(response, `inventory_master_${supplier.toLowerCase()}.${ext}`);
    } catch (err) {
      const message = err?.message || 'Export failed';
      throw new Error(message);
    }
  },
  warmInventoryMasterExport: (supplier = 'ALL') =>
    apiClient
      .post(ENDPOINTS.INVENTORY.STOCK_WARM_INVENTORY_MASTER, null, { params: { supplier } })
      .catch(() => {}),
  importInventoryMaster: async (forceOpening = false) =>
    unwrapData(
      await apiClient.post(ENDPOINTS.INVENTORY.STOCK_IMPORT_INVENTORY_MASTER, null, {
        params: forceOpening ? { force_opening: true } : {},
      })
    ),
  transactions: async (params) => unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.TRANSACTIONS, { params: buildListParams(params) })),
  transaction: async (id) => unwrapData(await apiClient.get(ENDPOINTS.INVENTORY.TRANSACTION(id))),
  ledger: async (params) => unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.LEDGER, { params: buildListParams(params) })),
};
