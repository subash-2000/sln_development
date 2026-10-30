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
    throw new Error('Invalid download response.');
  }
  const header = await blob.slice(0, 5).text();
  if (!header.startsWith('%PDF')) {
    const text = await blob.text();
    try {
      const body = JSON.parse(text);
      throw new Error(body?.message || 'PDF download failed on the server.');
    } catch (parseErr) {
      if (parseErr instanceof Error && parseErr.message !== text) {
        throw parseErr;
      }
      throw new Error(text?.slice(0, 240) || 'PDF download failed on the server.');
    }
  }
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 2000);
};

export const logisticsApi = {
  inward: {
    create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.LOGISTICS.INWARD, data)),
    downloadInvoicePdf: async (transactionId) => {
      const response = await apiClient.get(ENDPOINTS.LOGISTICS.INWARD_INVOICE_PDF(transactionId), {
        responseType: 'blob',
        headers: { Accept: 'application/pdf' },
      });
      await downloadBlob(response, `inward-invoice-${transactionId}.pdf`);
    },
    parseDocument: async (file) => {
      const form = new FormData();
      form.append('file', file);
      return unwrapData(
        await apiClient.post(ENDPOINTS.LOGISTICS.INWARD_PARSE, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      );
    },
  },
  dispatch: {
    list: async (params) =>
      unwrapList(await apiClient.get(ENDPOINTS.LOGISTICS.DISPATCH, { params: buildListParams(params) })),
    getById: async (id) => unwrapData(await apiClient.get(ENDPOINTS.LOGISTICS.DISPATCH_DETAIL(id))),
    create: async (data) => unwrapData(await apiClient.post(ENDPOINTS.LOGISTICS.DISPATCH, data)),
    confirm: async (id) => unwrapData(await apiClient.post(ENDPOINTS.LOGISTICS.DISPATCH_CONFIRM(id), {})),
  },
  gatePasses: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.LOGISTICS.GATE_PASSES, { params: buildListParams(params) })),
};
