import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

const download = async (url, fallbackName) => {
  const response = await apiClient.get(url, { responseType: 'blob' });
  const blob = response instanceof Blob ? response : response?.data;
  if (!(blob instanceof Blob)) throw new Error('Invalid download response.');
  if (blob.type?.includes('json')) {
    const payload = JSON.parse(await blob.text());
    throw new Error(payload?.message || 'Download failed.');
  }
  const disposition = response?.headers?.['content-disposition'] || '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || fallbackName;
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(objectUrl), 2000);
};

export const billingApi = {
  periods: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.PERIODS, { params: buildListParams(params) })),
  documents: async (params) => unwrapList(await apiClient.get(ENDPOINTS.BILLING.DOCUMENTS, { params: buildListParams(params) })),
  createPeriod: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.PERIODS, data)),
  calculate: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.CALCULATE, data)),
  document: async (id) => unwrapData(await apiClient.get(ENDPOINTS.BILLING.DOCUMENT(id))),
  downloadPdf: (id, number) => download(ENDPOINTS.BILLING.PDF(id), `${number || 'billing-statement'}.pdf`),
  downloadExcel: (id, number) => download(ENDPOINTS.BILLING.EXCEL(id), `${number || 'billing-statement'}.xlsx`),
  confirm: async (id) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.CONFIRM(id))),
  addManualCharge: async (id, data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.MANUAL_CHARGES(id), data)),
  updateTotal: async (id, totalAmount) => unwrapData(await apiClient.patch(`/billing/documents/${id}/total`, { total_amount: totalAmount })),
  runMonthEnd: async (data) => unwrapData(await apiClient.post(ENDPOINTS.BILLING.MONTH_END_RUN, data)),
};
