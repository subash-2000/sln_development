import React, { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import DataTable from '../../../components/tables/DataTable';
import apiClient from '../../../services/api/client';
import { unwrapData, unwrapList } from '../../../services/api/unwrap';
import { useCustomers } from '../../customers/hooks/use-customers';
import { ringsApi } from '../../rings/api/rings.api';

const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';
const initial = () => ({
  customer_id: '',
  delivery_challan_id: '',
  invoice_number: '',
  invoice_date: new Date().toISOString().slice(0, 10),
  invoice_amount: '',
  tax_amount: '0',
  remarks: '',
});

export default function SalesTaxTrackingPage() {
  const queryClient = useQueryClient();
  const [show, setShow] = useState(false);
  const [form, setForm] = useState(initial);
  const { data: customers } = useCustomers({ page_size: 200, status: 'ACTIVE' });
  const { data: challans } = useQuery({
    queryKey: ['outward-challans'],
    queryFn: () => ringsApi.listDocuments({ document_type: 'OUTWARD', page_size: 200 }),
  });
  const { data, isLoading } = useQuery({
    queryKey: ['sales-tax-tracking'],
    queryFn: async () =>
      unwrapList(await apiClient.get('/sales-tax-invoices', { params: { page_size: 200 } })),
  });
  const available = (challans?.items || []).filter(
    (item) => !form.customer_id || item.customer_id === form.customer_id
  );
  const create = useMutation({
    mutationFn: async (payload) => unwrapData(await apiClient.post('/sales-tax-invoices', payload)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-tax-tracking'] });
      setShow(false);
      setForm(initial());
    },
  });
  const columns = useMemo(
    () => [
      { key: 'customer_name', label: 'Customer' },
      { key: 'delivery_challan_number', label: 'Delivery Challan' },
      { key: 'invoice_number', label: 'Invoice No.' },
      { key: 'invoice_date', label: 'Invoice Date', type: 'date' },
      { key: 'invoice_amount', label: 'Invoice Amount', type: 'currency' },
      { key: 'tax_amount', label: 'Tax', type: 'currency' },
      { key: 'remarks', label: 'Remarks' },
    ],
    []
  );
  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales Tax Invoice Tracking"
        description="Track sales tax invoices received against Delivery Challans."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Sales Tax Invoices' },
        ]}
        actions={<Button onClick={() => setShow(true)}>Track Invoice</Button>}
      />
      {show && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          onMouseDown={(event) => event.target === event.currentTarget && setShow(false)}
        >
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-xl">
            <Card.Header className="sticky top-0 z-10 flex items-center justify-between bg-white">
              <Card.Title>Track Sales Tax Invoice</Card.Title>
              <button type="button" aria-label="Close" onClick={() => setShow(false)}>
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </Card.Header>
            <Card.Body>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  create.mutate({
                    ...form,
                    invoice_amount: Number(form.invoice_amount),
                    tax_amount: Number(form.tax_amount),
                  });
                }}
                className="grid grid-cols-1 md:grid-cols-3 gap-5"
              >
                <label className={label}>
                  Customer *
                  <select
                    required
                    className={field}
                    value={form.customer_id}
                    onChange={(event) =>
                      setForm({ ...form, customer_id: event.target.value, delivery_challan_id: '' })
                    }
                  >
                    <option value="">Select customer</option>
                    {(customers?.items || []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={label}>
                  Delivery Challan *
                  <select
                    required
                    className={field}
                    value={form.delivery_challan_id}
                    onChange={set('delivery_challan_id')}
                  >
                    <option value="">Select challan</option>
                    {available.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.sln_challan_number || item.document_number}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={label}>
                  Invoice Number *
                  <input
                    required
                    className={field}
                    value={form.invoice_number}
                    onChange={set('invoice_number')}
                  />
                </label>
                <label className={label}>
                  Invoice Date *
                  <input
                    required
                    type="date"
                    className={field}
                    value={form.invoice_date}
                    onChange={set('invoice_date')}
                  />
                </label>
                <label className={label}>
                  Invoice Amount *
                  <input
                    required
                    type="number"
                    min="0"
                    step="0.01"
                    className={field}
                    value={form.invoice_amount}
                    onChange={set('invoice_amount')}
                  />
                </label>
                <label className={label}>
                  Tax Amount
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className={field}
                    value={form.tax_amount}
                    onChange={set('tax_amount')}
                  />
                </label>
                <label className={`${label} md:col-span-3`}>
                  Remarks
                  <textarea
                    className={`${field} min-h-20 resize-y`}
                    value={form.remarks}
                    onChange={set('remarks')}
                  />
                </label>
                {create.error && (
                  <div className="md:col-span-3 text-sm text-red-600">
                    {create.error.response?.data?.message || create.error.message}
                  </div>
                )}
                <div className="md:col-span-3 flex justify-end gap-3 border-t border-gray-100 pt-4">
                  <Button type="button" variant="secondary" onClick={() => setShow(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={create.isPending}>
                    Save
                  </Button>
                </div>
              </form>
            </Card.Body>
          </Card>
        </div>
      )}
      <DataTable
        columns={columns}
        data={data?.items || []}
        isLoading={isLoading}
        emptyTitle="No sales tax invoices tracked"
      />
    </div>
  );
}
