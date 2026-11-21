import React, { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import DataTable from '../../../components/tables/DataTable';
import StatusBadge from '../../../components/ui/StatusBadge';
import { billingApi } from '../api/billing.api';

const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';
const money = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value || 0));

export default function BillingDetailPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ description: '', quantity: '1', rate: '', remarks: '' });
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
  const columns = useMemo(
    () => [
      { key: 'service_type', label: 'Service' },
      { key: 'calculation_basis', label: 'Basis' },
      { key: 'quantity', label: 'Quantity', type: 'number' },
      { key: 'rate', label: 'Rate', type: 'currency' },
      { key: 'amount', label: 'Amount', type: 'currency' },
      { key: 'description', label: 'Description' },
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

  return (
    <div className="space-y-6">
      <PageHeader
        title={document.billing_number}
        description={`${document.customer_name || ''} · ${document.period_name || ''}`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Billing', to: '/finance/billing' },
          { label: document.billing_number },
        ]}
        actions={
          document.status === 'DRAFT' ? (
            <Button
              isLoading={confirm.isPending}
              onClick={() => window.confirm('Finalize this bill?') && confirm.mutate()}
            >
              Finalize Bill
            </Button>
          ) : null
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          ['Status', <StatusBadge key="status" status={document.status} />],
          ['Subtotal', money(document.subtotal_amount)],
          ['Tax', money(document.tax_amount)],
          ['Total', money(document.total_amount)],
        ].map(([name, value]) => (
          <Card key={name} className="p-4">
            <div className="text-xs font-medium text-gray-500">{name}</div>
            <div className="mt-1 text-xl font-bold text-gray-900">{value}</div>
          </Card>
        ))}
      </div>
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Service Lines</h2>
        <DataTable
          columns={columns}
          data={document.lines || []}
          emptyTitle="No billing service lines"
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
