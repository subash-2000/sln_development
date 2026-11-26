import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import DataTable from '../../../components/tables/DataTable';
import StatusBadge from '../../../components/ui/StatusBadge';
import { billingApi } from '../api/billing.api';
import { FileDown, FileSpreadsheet } from 'lucide-react';

const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';
const money = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value || 0));

export default function BillingDetailPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ description: '', quantity: '1', rate: '', remarks: '' });
  const [totalInput, setTotalInput] = useState('');
  const {
    data: document,
    isLoading,
    error,
  } = useQuery({ queryKey: ['billing-document', id], queryFn: () => billingApi.document(id) });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['billing-document', id] });
    queryClient.invalidateQueries({ queryKey: ['billing-documents'] });
  };
  const add = useMutation({
    mutationFn: () =>
      billingApi.addManualCharge(id, {
        ...form,
        quantity: Number(form.quantity),
        rate: Number(form.rate),
      }),
    onSuccess: () => {
      refresh();
      setForm({ description: '', quantity: '1', rate: '', remarks: '' });
    },
  });
  const confirm = useMutation({ mutationFn: () => billingApi.confirm(id), onSuccess: refresh });
  const updateTotal = useMutation({
    mutationFn: () => billingApi.updateTotal(id, Number(totalInput)),
    onSuccess: refresh,
  });
  useEffect(() => {
    if (document) {
      const hasData = (document.lines || []).some((line) => Number(line.quantity || 0) > 0);
      setTotalInput(String(hasData ? (document.total_amount ?? '0') : '0'));
    }
  }, [document]);
  const columns = useMemo(
    () => [
      { key: 'service_type', label: 'Service' },
      { key: 'inward_reference', label: 'Invoice / Inward Ref' },
      { key: 'product_sku', label: 'Product' },
      { key: 'inward_date', label: 'Inward Date', type: 'date' },
      { key: 'charge_from', label: 'From', type: 'date' },
      { key: 'charge_to', label: 'To', type: 'date' },
      { key: 'age_days', label: 'Age (Days)', type: 'number' },
      { key: 'received_quantity', label: 'Inward Qty', type: 'number' },
      { key: 'dispatched_quantity', label: 'Dispatched Qty', type: 'number' },
      { key: 'balance_quantity', label: 'Balance Qty', type: 'number' },
      { key: 'quantity_days', label: 'Qty × Days', type: 'number' },
      { key: 'rate', label: 'Rate', type: 'currency' },
      { key: 'amount', label: 'Amount', type: 'currency' },
    ],
    []
  );
  if (isLoading) return <div className="text-sm text-gray-500">Loading billing document…</div>;
  if (error || !document)
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error?.response?.data?.message || error?.message || 'Billing document not found'}
      </div>
    );
  const billableLines = (document.lines || []).filter((line) => Number(line.quantity || 0) > 0);
  const hasBillingData = billableLines.length > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title={document.billing_number}
        description={`${document.vendor_name || ''} · ${document.period_name || ''}`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Billing', to: '/finance/billing' },
          { label: document.billing_number },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" leftIcon={<FileDown size={16} />} onClick={() => billingApi.downloadPdf(id, document.billing_number)}>
              PDF
            </Button>
            <Button variant="secondary" leftIcon={<FileSpreadsheet size={16} />} onClick={() => billingApi.downloadExcel(id, document.billing_number)}>
              Excel
            </Button>
            {document.status === 'DRAFT' && hasBillingData ? (
              <Button
                isLoading={confirm.isPending}
                onClick={() => window.confirm('Finalize this bill?') && confirm.mutate()}
              >
                Finalize Bill
              </Button>
            ) : null}
          </div>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          ['Status', <StatusBadge key="status" status={document.status} />],
          ['Subtotal', money(hasBillingData ? document.subtotal_amount : 0)],
          ['Tax', money(hasBillingData ? document.tax_amount : 0)],
        ].map(([name, value]) => (
          <Card key={name} className="p-4">
            <div className="text-xs font-medium text-gray-500">{name}</div>
            <div className="mt-1 text-xl font-bold text-gray-900">{value}</div>
          </Card>
        ))}
        <Card className="p-4">
          <div className="text-xs font-medium text-gray-500">Total</div>
          {document.status === 'DRAFT' && hasBillingData ? (
            <div className="mt-2 flex items-center gap-2">
              <input
                type="number"
                min="0"
                step="0.01"
                className={field}
                value={totalInput}
                onChange={(event) => setTotalInput(event.target.value)}
              />
              <Button size="sm" isLoading={updateTotal.isPending} onClick={() => updateTotal.mutate()}>
                Save
              </Button>
            </div>
          ) : (
            <div className="mt-1 text-xl font-bold text-gray-900">{money(hasBillingData ? document.total_amount : 0)}</div>
          )}
        </Card>
      </div>
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Service Lines</h2>
        <DataTable
          columns={columns}
          data={billableLines}
          emptyTitle="No inward or product data found for the selected dates"
        />
      </div>
      {document.status === 'DRAFT' && (
        <Card>
          <Card.Header>
            <Card.Title>Add Manual Charge</Card.Title>
          </Card.Header>
          <Card.Body>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                add.mutate();
              }}
              className="grid grid-cols-1 md:grid-cols-4 gap-5"
            >
              <label className={label}>
                Description *
                <input
                  required
                  className={field}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                />
              </label>
              <label className={label}>
                Quantity *
                <input
                  required
                  type="number"
                  min="0.0001"
                  step="0.0001"
                  className={field}
                  value={form.quantity}
                  onChange={(event) => setForm({ ...form, quantity: event.target.value })}
                />
              </label>
              <label className={label}>
                Rate *
                <input
                  required
                  type="number"
                  min="0"
                  step="0.0001"
                  className={field}
                  value={form.rate}
                  onChange={(event) => setForm({ ...form, rate: event.target.value })}
                />
              </label>
              <div className="flex items-end">
                <Button type="submit" isLoading={add.isPending}>
                  Add Charge
                </Button>
              </div>
              {add.error && (
                <div className="md:col-span-4 text-sm text-red-600">
                  {add.error.response?.data?.message || add.error.message}
                </div>
              )}
            </form>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}
