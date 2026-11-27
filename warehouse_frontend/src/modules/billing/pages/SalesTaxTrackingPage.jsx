import React, { useMemo, useRef, useState } from 'react';
import { FileUp, Upload, X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import DataTable from '../../../components/tables/DataTable';
import StatusBadge from '../../../components/ui/StatusBadge';
import apiClient from '../../../services/api/client';
import { unwrapData, unwrapList } from '../../../services/api/unwrap';

const field = 'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';
const emptyForm = () => ({
  delivery_challan_id: '', invoice_number: '', invoice_date: '',
  invoice_amount: '', tax_amount: '0', remarks: '',
  packing_weight: '', gross_weight: '', eway_bill_number: '', ackn_copies_status: '',
});

export default function SalesTaxTrackingPage() {
  const invoiceInputRef = useRef(null);
  const queryClient = useQueryClient();
  const [show, setShow] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [selectedDispatch, setSelectedDispatch] = useState(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ['sales-tax-tracking'],
    queryFn: async () => unwrapList(await apiClient.get('/sales-tax-invoices', { params: { page_size: 200 } })),
  });
  const openTracking = (dispatch) => {
    setSelectedDispatch(dispatch);
    setForm({
      ...emptyForm(), delivery_challan_id: dispatch.delivery_challan_id,
      ...(dispatch.id ? {
        invoice_number: dispatch.invoice_number, invoice_date: dispatch.invoice_date,
        invoice_amount: dispatch.invoice_amount, tax_amount: dispatch.tax_amount,
        remarks: dispatch.remarks ?? '', packing_weight: dispatch.packing_weight ?? '',
        gross_weight: dispatch.gross_weight ?? '', eway_bill_number: dispatch.eway_bill_number ?? '',
        ackn_copies_status: dispatch.ackn_copies_status ?? '',
      } : {}),
    });
    create.reset();
    scan.reset();
    setShow(true);
  };
  const create = useMutation({
    mutationFn: async (payload) => {
      const details = {
        invoice_number: payload.invoice_number.trim(),
        invoice_date: payload.invoice_date,
        invoice_amount: payload.invoice_amount,
        tax_amount: payload.tax_amount || '0',
        packing_weight: payload.packing_weight || null,
        gross_weight: payload.gross_weight || null,
        eway_bill_number: payload.eway_bill_number.trim() || null,
        ackn_copies_status: payload.ackn_copies_status.trim() || null,
        remarks: payload.remarks.trim() || null,
      };
      return selectedDispatch.id
        ? unwrapData(await apiClient.patch(`/sales-tax-invoices/${selectedDispatch.id}/details`, details))
        : unwrapData(await apiClient.post('/sales-tax-invoices', {
        delivery_challan_id: payload.delivery_challan_id,
        ...details,
      }));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-tax-tracking'] });
      setShow(false);
      setSelectedDispatch(null);
      setForm(emptyForm());
    },
  });
  const scan = useMutation({
    mutationFn: async (file) => {
      const upload = new FormData();
      upload.append('file', file);
      return unwrapData(await apiClient.post('/sales-tax-invoices/scan', upload, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      }));
    },
    onSuccess: (details) => setForm((current) => {
      const scanned = Object.fromEntries(Object.entries(details).map(([key, value]) => [key, value == null ? '' : String(value)]));
      return { ...current, ...scanned };
    }),
  });
  const columns = useMemo(() => [
    { key: 'dispatch_date', label: 'Dispatch Date', type: 'date' },
    { key: 'dispatch_number', label: 'Dispatch No.' },
    { key: 'delivery_challan_number', label: 'Delivery Challan' },
    { key: 'supplier_name', label: 'Supplier' },
    { key: 'customer_name', label: 'Dispatched To' },
    { key: 'vehicle_number', label: 'Vehicle No.' },
    { key: 'invoice_number', label: 'Supplier Tax Invoice' },
    { key: 'invoice_date', label: 'Invoice Date', type: 'date' },
    { key: 'invoice_amount', label: 'Invoice Amount', type: 'currency' },
    { key: 'tax_amount', label: 'Tax', type: 'currency' },
    { key: 'packing_weight', label: 'Packaging Weight (kg)' },
    { key: 'gross_weight', label: 'Gross Weight (kg)' },
    { key: 'eway_bill_number', label: 'E-Way Bill Number' },
    { key: 'remarks', label: 'Remark' },
    { key: 'ackn_copies_status', label: 'ACKN Copies Status' },
    { key: 'tracking_status', label: 'Status', render: (value) => <StatusBadge status={value} /> },
  ], []);
  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Tax Invoice Tracking"
        description="Posted dispatches and the supplier tax invoices received against them."
        breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Finance' }, { label: 'Supplier Tax Invoices' }]}
      />
      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        error={error}
        emptyTitle="No posted dispatches found"
        emptyDescription="Posted outward dispatches will automatically appear here."
        actions={(row) => row.tracking_status === 'PENDING' ? (
          <Button size="sm" onClick={() => openTracking(row)}>Capture Invoice</Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => openTracking(row)}>Edit Details</Button>
        )}
      />
      {show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-xl">
            <Card.Header className="sticky top-0 z-10 flex items-center justify-between bg-white">
              <div>
                <Card.Title>{selectedDispatch?.id ? 'Edit Supplier Invoice Details' : 'Capture Supplier Tax Invoice'}</Card.Title>
                <p className="mt-1 text-sm text-gray-500">
                  {selectedDispatch?.supplier_name} · {selectedDispatch?.delivery_challan_number}
                </p>
              </div>
              <button type="button" aria-label="Close" disabled={scan.isPending || create.isPending} onClick={() => setShow(false)}><X className="h-5 w-5 text-gray-500" /></button>
            </Card.Header>
            <Card.Body>
              <form onSubmit={(event) => { event.preventDefault(); if (!scan.isPending && !create.isPending) create.mutate(form); }} className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="flex justify-end md:col-span-3">
                  <input ref={invoiceInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" className="hidden" disabled={scan.isPending || create.isPending}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = '';
                      if (file) scan.mutate(file);
                    }} />
                  <Button type="button" size="sm" variant="secondary"
                    leftIcon={<Upload size={16} />} isLoading={scan.isPending}
                    isDisabled={create.isPending} onClick={() => invoiceInputRef.current?.click()}>
                    {scan.isPending ? 'Reading…' : 'Upload Invoice (PDF / Image)'}
                  </Button>
                </div>
                {scan.isPending && <p role="status" className="md:col-span-3 text-sm text-gray-600">Reading invoice…</p>}
                {scan.isSuccess && <p role="status" className="md:col-span-3 text-sm text-gray-600">Review the captured values and fill any missing fields before saving. ACKN Copies Status is manual.</p>}
                {scan.error && <p role="alert" className="md:col-span-3 text-sm text-red-600">{scan.error.response?.data?.message || scan.error.message}</p>}
                <label className={label}>Dispatch Number<input readOnly className={`${field} bg-gray-50`} value={selectedDispatch?.dispatch_number || ''} /></label>
                <label className={label}>Delivery Challan<input readOnly className={`${field} bg-gray-50`} value={selectedDispatch?.delivery_challan_number || ''} /></label>
                <label className={label}>Supplier<input readOnly className={`${field} bg-gray-50`} value={selectedDispatch?.supplier_name || ''} /></label>
                <label className={label}>Tax Invoice Number *<input required maxLength={100} className={field} value={form.invoice_number} onChange={set('invoice_number')} /></label>
                <label className={label}>Invoice Date *<input required type="date" className={field} value={form.invoice_date} onChange={set('invoice_date')} /></label>
                <label className={label}>Invoice Amount *<input required type="number" min="0" step="0.01" className={field} value={form.invoice_amount} onChange={set('invoice_amount')} /></label>
                <label className={label}>Tax Amount<input type="number" min="0" step="0.01" className={field} value={form.tax_amount} onChange={set('tax_amount')} /></label>
                <label className={label}>Packaging Weight (kg)<input type="number" min="0" step="0.001" className={field} value={form.packing_weight} onChange={set('packing_weight')} /></label>
                <label className={label}>Gross Weight (kg)<input type="number" min="0" step="0.001" className={field} value={form.gross_weight} onChange={set('gross_weight')} /></label>
                <label className={label}>E-Way Bill Number<input maxLength={100} className={field} value={form.eway_bill_number} onChange={set('eway_bill_number')} /></label>
                <label className={label}>ACKN Copies Status (Manual)<input maxLength={100} className={field} value={form.ackn_copies_status} onChange={set('ackn_copies_status')} /></label>
                <label className={`${label} md:col-span-3`}>Remarks<textarea className={`${field} min-h-20 resize-y`} value={form.remarks} onChange={set('remarks')} /></label>
                {create.error && <div className="md:col-span-3 text-sm text-red-600">{create.error.response?.data?.message || create.error.message}</div>}
                <div className="md:col-span-3 flex justify-end gap-3 border-t border-gray-100 pt-4">
                  <Button type="button" variant="secondary" isDisabled={scan.isPending || create.isPending} onClick={() => setShow(false)}>Cancel</Button>
                  <Button type="submit" isDisabled={scan.isPending} isLoading={create.isPending} leftIcon={<FileUp size={16} />}>Save Invoice Details</Button>
                </div>
              </form>
            </Card.Body>
          </Card>
        </div>
      )}
    </div>
  );
}
