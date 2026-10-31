import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapList } from '../../../services/api/unwrap';

export const reportsApi = {
  // 1. Vehicle Movement Reports
  getVehicleReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.VEHICLES, {
        params: buildListParams(params),
      })
    );
  },

  // 2. Inward Stock Receipt Reports
  getInwardReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.INWARD, {
        params: buildListParams(params),
      })
    );
  },

  // 3. Outward Dispatch Reports
  getOutwardReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.OUTWARD, {
        params: buildListParams(params),
      })
    );
  },

  // 4. Daily Stock Reports
  getDailyStockReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.CURRENT_STOCK, {
        params: buildListParams(params),
      })
    );
  },

  // 5. Invoice & GST Reports
  getInvoiceReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.SALES, {
        params: buildListParams(params),
      })
    );
  },

  // 6. Supplier Wise Stock & Inventory Reports
  getSupplierStockReports: async (params = {}) => {
    return unwrapList(
      await apiClient.get(ENDPOINTS.REPORTS.VENDOR_STOCK, {
        params: buildListParams(params),
      })
    );
  },
};

export * from '../utils/excel-export';

/**
 * Utility to download tabular report data as CSV
 * @param {Array<string>} headers - Header column titles
 * @param {Array<Array<any>>} rows - Matrix of row cells
 * @param {string} filename - Target file name
 */
export const exportReportToCsv = (headers, rows, filename = 'report.csv') => {
  const sanitize = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const csvContent = [
    headers.map(sanitize).join(','),
    ...rows.map((row) => row.map(sanitize).join(',')),
  ].join('\r\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
