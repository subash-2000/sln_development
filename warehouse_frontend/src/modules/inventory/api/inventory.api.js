import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

const asBlob = (payload) => {
  if (payload instanceof Blob) return payload;
  if (payload?.data instanceof Blob) return payload.data;
  if (payload != null) return new Blob([payload]);
  return null;
};

const downloadBlob = async (response, fallbackName) => {
  const blob = asBlob(response);
  if (!blob || blob.size === 0) {
    throw new Error('Export file was empty or invalid. Please try again.');
  }

  // If server returned a JSON error payload disguised in a Blob
  if (blob.type && blob.type.includes('json')) {
    try {
      const text = await blob.text();
      const errObj = JSON.parse(text);
      throw new Error(errObj?.message || errObj?.detail || 'Export failed on the server. Please try again.');
    } catch (parseErr) {
      if (parseErr.message && !parseErr.message.includes('JSON')) {
        throw parseErr;
      }
      throw new Error('Export failed on the server. Please try again.');
    }
  }

  const disposition =
    response?.headers?.['content-disposition'] ||
    response?.headers?.['Content-Disposition'] ||
    '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 1000);
};

export const inventoryApi = {
  stock: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.STOCK, { params: buildListParams(params) })),

  exportInventoryMaster: async (supplier = 'ALL') => {
    const response = await apiClient.get(ENDPOINTS.INVENTORY.STOCK_EXPORT_INVENTORY_MASTER, {
      params: { supplier },
      responseType: 'blob',
    });
    const ext = supplier === 'ALL' ? 'zip' : 'xlsx';
    await downloadBlob(response, `inventory_master_${supplier.toLowerCase()}.${ext}`);
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

  transactions: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.TRANSACTIONS, { params: buildListParams(params) })),

  transaction: async (id) => unwrapData(await apiClient.get(ENDPOINTS.INVENTORY.TRANSACTION(id))),

  ledger: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.INVENTORY.LEDGER, { params: buildListParams(params) })),
};
