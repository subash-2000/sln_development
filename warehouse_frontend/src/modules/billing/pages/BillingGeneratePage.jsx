import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import { billingApi } from '../api/billing.api';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';
import apiClient from '../../../services/api/client';
import { unwrapList } from '../../../services/api/unwrap';

const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all duration-200';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';

export default function BillingGeneratePage() {
  const navigate = useNavigate();
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
  const [form, setForm] = useState({
    period_name: `${now.toLocaleString('en', { month: 'long' })} ${now.getFullYear()}`,
    start_date: first,
    end_date: last,
    customer_id: '',
    warehouse_id: '',
    rate_card_id: '',
    tax_rate_percent: '0',
    notes: '',
  });
  const { data: customerData, isLoading: customersLoading } = useCustomers({
    page_size: 200,
    status: 'ACTIVE',
  });
  const { data: warehouseData, isLoading: warehousesLoading } = useWarehouses({
    page_size: 200,
    status: 'ACTIVE',
  });
  const { data: rateData, isLoading: ratesLoading } = useQuery({
    queryKey: ['customer-pricing'],
    queryFn: async () =>
      unwrapList(await apiClient.get('/rate-cards', { params: { page_size: 200 } })),
  });
  const customers = customerData?.items || [];
  const warehouses = warehouseData?.items || [];
  const rates = useMemo(
    () => (rateData?.items || []).filter((rate) => rate.customer_id === form.customer_id),
    [rateData, form.customer_id]
  );
  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const generate = useMutation({
    mutationFn: async () => {
      const periods = await billingApi.periods({ page_size: 100 });
      let period = periods.items.find((item) => item.period_name === form.period_name);
      if (!period)
        period = await billingApi.createPeriod({
          period_name: form.period_name,
          start_date: form.start_date,
          end_date: form.end_date,
          billing_cycle: 'MONTHLY',
        });
      return billingApi.calculate({
        billing_period_id: period.id,
        warehouse_id: form.warehouse_id,
        customer_id: form.customer_id,
        rate_card_id: form.rate_card_id,
        tax_rate_percent: Number(form.tax_rate_percent),
        notes: form.notes || null,
      });
    },
    onSuccess: (document) => navigate(`/finance/billing/${document.id}`),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Generate Monthly Bill"
        description="Calculate customer warehouse charges from pricing and recorded WMS activity."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Billing', to: '/finance/billing' },
          { label: 'Generate' },
        ]}
      />
      <Card>
        <Card.Header>
          <Card.Title>Billing Information</Card.Title>
        </Card.Header>
        <Card.Body>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              generate.mutate();
            }}
            className="grid grid-cols-1 md:grid-cols-3 gap-5"
          >
            <label className={label}>
              Period Name *
              <input
                required
                className={field}
                value={form.period_name}
                onChange={set('period_name')}
              />
            </label>
            <label className={label}>
              Period From *
              <input
                required
                type="date"
                className={field}
                value={form.start_date}
                onChange={set('start_date')}
              />
            </label>
            <label className={label}>
              Period To *
              <input
                required
                type="date"
                min={form.start_date}
                className={field}
                value={form.end_date}
                onChange={set('end_date')}
              />
            </label>
            <label className={label}>
              Customer *
              <select
                required
                className={field}
                value={form.customer_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    customer_id: event.target.value,
                    rate_card_id: '',
                  }))
                }
              >
                <option value="">
                  {customersLoading ? 'Loading customers…' : 'Select customer'}
                </option>
                {customers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className={label}>
              Warehouse *
              <select
                required
                className={field}
                value={form.warehouse_id}
                onChange={set('warehouse_id')}
              >
                <option value="">
                  {warehousesLoading ? 'Loading warehouses…' : 'Select warehouse'}
                </option>
                {warehouses.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className={label}>
              Customer Pricing *
              <select
                required
                disabled={!form.customer_id || ratesLoading}
                className={field}
                value={form.rate_card_id}
                onChange={set('rate_card_id')}
              >
                <option value="">
                  {!form.customer_id
                    ? 'Select customer first'
                    : ratesLoading
                      ? 'Loading pricing…'
                      : rates.length
                        ? 'Select pricing'
                        : 'No active pricing found'}
                </option>
                {rates.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.code})
                  </option>
                ))}
              </select>
            </label>
            <label className={label}>
              Tax Rate %
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className={field}
                value={form.tax_rate_percent}
                onChange={set('tax_rate_percent')}
              />
            </label>
            <label className={`${label} md:col-span-2`}>
              Notes
              <textarea
                className={`${field} min-h-20 resize-y`}
                value={form.notes}
                onChange={set('notes')}
              />
            </label>
            {generate.error && (
              <div className="md:col-span-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {generate.error.response?.data?.message || generate.error.message}
              </div>
            )}
            <div className="md:col-span-3 flex justify-end gap-3 border-t border-gray-100 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/finance/billing')}
              >
                Cancel
              </Button>
              <Button type="submit" isLoading={generate.isPending}>
                Generate Draft Bill
              </Button>
            </div>
          </form>
        </Card.Body>
      </Card>
    </div>
  );
}
