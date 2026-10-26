import apiClient from '../../../services/api/client';
import { ENDPOINTS } from '../../../services/api/endpoints';
import { buildListParams, unwrapData, unwrapList } from '../../../services/api/unwrap';

const triggerDownload = (blob, filename) => {
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

const filenameFromDisposition = (disposition, fallbackName) => {
  const match = (disposition || '').match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallbackName;
};

const parseErrorBlob = async (blob, fallback) => {
  const text = await blob.text();
  try {
    const body = JSON.parse(text);
    throw new Error(body?.message || fallback);
  } catch (parseErr) {
    if (parseErr instanceof Error && parseErr.message !== text) {
      throw parseErr;
    }
    throw new Error(text?.slice(0, 240) || fallback);
  }
};

const asBlob = (payload) => {
  if (payload instanceof Blob) return payload;
  if (payload?.data instanceof Blob) return payload.data;
  return null;
};

const dispositionOf = (payload) =>
  payload?.headers?.['content-disposition'] || payload?.headers?.['Content-Disposition'] || '';

const downloadPdf = async (response, fallbackName) => {
  const blob = asBlob(response);
  if (!blob) {
    throw new Error('Invalid download response.');
  }
  const header = await blob.slice(0, 5).text();
  if (!header.startsWith('%PDF')) {
    await parseErrorBlob(blob, 'PDF download failed on the server.');
  }
  triggerDownload(blob, filenameFromDisposition(dispositionOf(response), fallbackName));
};

const downloadXlsx = async (response, fallbackName) => {
  const blob = asBlob(response);
  if (!blob) {
    throw new Error('Invalid download response.');
  }
  const header = await blob.slice(0, 2).text();
  if (header !== 'PK') {
    await parseErrorBlob(blob, 'Excel download failed on the server.');
  }
  triggerDownload(blob, filenameFromDisposition(dispositionOf(response), fallbackName));
};

const getFile = async (url, fallbackName, params, accept, save) => {
  const response = await apiClient.get(url, {
    params: params ? buildListParams(params) : undefined,
    responseType: 'blob',
    headers: { Accept: accept },
  });
  await save(response, fallbackName);
};

const getPdf = (url, fallbackName, params) =>
  getFile(url, fallbackName, params, 'application/pdf', downloadPdf);

const getXlsx = (url, fallbackName, params) =>
  getFile(
    url,
    fallbackName,
    params,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    downloadXlsx
  );

export const ringsApi = {
  listDocuments: async (params) =>
    unwrapList(await apiClient.get(ENDPOINTS.RINGS.DOCUMENTS, { params: buildListParams(params) })),
  getDocument: async (id) => unwrapData(await apiClient.get(ENDPOINTS.RINGS.DOCUMENT(id))),
  createInward: async (data) => unwrapData(await apiClient.post(ENDPOINTS.RINGS.INWARD, data)),
  supplierTypes: async (vendorId) =>
    unwrapData(await apiClient.get(ENDPOINTS.RINGS.SUPPLIER_TYPES, { params: { vendor_id: vendorId } })),
  createPick: async (data) => unwrapData(await apiClient.post(ENDPOINTS.RINGS.PICKS, data)),
  dispatchPick: async (id, data) => unwrapData(await apiClient.post(ENDPOINTS.RINGS.DISPATCH(id), data || {})),
  stock: async (params) => unwrapData(await apiClient.get(ENDPOINTS.RINGS.STOCK, { params: buildListParams(params) })),
  dayClose: async (params) =>
    unwrapData(await apiClient.get(ENDPOINTS.RINGS.DAY_CLOSE, { params: buildListParams(params) })),
  sales: async (params) => unwrapData(await apiClient.get(ENDPOINTS.RINGS.SALES, { params: buildListParams(params) })),
  downloadChallanPdf: (id) => getPdf(ENDPOINTS.RINGS.CHALLAN_PDF(id), `sln-challan-${id}.pdf`),
  downloadChallanXlsx: (id) => getXlsx(ENDPOINTS.RINGS.CHALLAN_XLSX(id), `sln-challan-${id}.xlsx`),
  downloadPickPdf: (id) => getPdf(ENDPOINTS.RINGS.PICK_PDF(id), `rings-pick-${id}.pdf`),
  downloadPickXlsx: (id) => getXlsx(ENDPOINTS.RINGS.PICK_XLSX(id), `rings-pick-${id}.xlsx`),
  downloadPicksPdf: (params) => getPdf(ENDPOINTS.RINGS.PICKS_PDF, 'rings-picking-list.pdf', params),
  downloadPicksXlsx: (params) => getXlsx(ENDPOINTS.RINGS.PICKS_XLSX, 'rings-picking-list.xlsx', params),
  downloadSalesPdf: (params) => getPdf(ENDPOINTS.RINGS.SALES_PDF, 'rings-sales-statement.pdf', params),
  downloadChallansPdf: (params) => getPdf(ENDPOINTS.RINGS.CHALLANS_PDF, 'sln-to-supplier-challans.pdf', params),
  downloadChallansXlsx: (params) => getXlsx(ENDPOINTS.RINGS.CHALLANS_XLSX, 'sln-to-supplier-challans.xlsx', params),
};
