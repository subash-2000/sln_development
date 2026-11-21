import React, { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import DataTable from '../../../components/tables/DataTable';
import apiClient from '../../../services/api/client';
import { unwrapList } from '../../../services/api/unwrap';
import { useCustomers } from '../../customers/hooks/use-customers';
import { useAuthStore } from '../../../store/auth.store';

const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all duration-200';
const label = 'block text-sm font-medium text-gray-700 space-y-1.5';
const services = ['HANDLING_IN', 'HANDLING_OUT', 'STORAGE', 'VALUE_ADDED_SERVICE', 'OTHER'];
const bases = [
  'PER_TRANSACTION',
  'PER_BAG_PER_DAY',
  'PER_MT_PER_DAY',
  'PER_SQFT_PER_MONTH',
  'FIXED',
];
const initialForm = () => ({
  customer_id: '',
  code: '',
  name: '',
  valid_from: new Date().toISOString().slice(0, 10),
  valid_to: '',
  service_type: 'HANDLING_IN',
  calculation_basis: 'PER_TRANSACTION',
  unit_rate: '',
  min_charge: '0',
});

export default function CustomerPricingPage() {
  const companyId = useAuthStore((state) => state.companyContext);
  const queryClient = useQueryClient();
  const [show, setShow] = useState(false);
  const [form, setForm] = useState(initialForm);
  const { data: customersData } = useCustomers({ page_size: 200, status: 'ACTIVE' });
  const { data, isLoading } = useQuery({
    queryKey: ['customer-pricing'],
    queryFn: async () =>
      unwrapList(await apiClient.get('/rate-cards', { params: { page_size: 200 } })),
  });
  const create = useMutation({
    mutationFn: (payload) => apiClient.post('/rate-cards', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer-pricing'] });
      setShow(false);
      setForm(initialForm());
    },
  });
  const cards = (data?.items || []).filter((card) => card.customer_id);
  const columns = useMemo(
    () => [
      { key: 'customer_name', label: 'Customer' },
      { key: 'code', label: 'Code', widthClass: 'w-36' },
      { key: 'name', label: 'Name' },
      { key: 'valid_from', label: 'Effective From', type: 'date', widthClass: 'w-40' },
      {
        key: 'valid_to',
        label: 'Effective To',
        type: 'date',
        widthClass: 'w-40',
        render: (value) => (value ? String(value).slice(0, 10) : 'Open'),
      },
      {
        key: 'items',
        label: 'Services',
        render: (items) =>
          (items || []).map((item) => `${item.service_type}: ₹${item.unit_rate}`).join(', ') || '—',
      },
      { key: 'status', label: 'Status', type: 'status', widthClass: 'w-32' },
    ],
    []
  );

  const save = async (event) => {
    event.preventDefault();
    try {
      await create.mutateAsync({
        company_id: companyId,
        customer_id: form.customer_id,
        vendor_id: null,
        code: form.code,
        name: form.name,
        valid_from: `${form.valid_from}T00:00:00Z`,
        valid_to: form.valid_to ? `${form.valid_to}T23:59:59Z` : null,
        currency: 'INR',
        items: [
          {
            service_type: form.service_type,
            calculation_basis: form.calculation_basis,
            unit_rate: Number(form.unit_rate),
            min_charge: Number(form.min_charge),
            currency: 'INR',
          },
        ],
      });
    } catch (error) {
      window.alert(error.response?.data?.message || error.message);
    }
  };
  const update = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Pricing Master"
        description="Effective-dated customer warehouse service rates."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Customer Pricing' },
        ]}
        actions={<Button onClick={() => setShow(true)}>New Pricing</Button>}
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
              <Card.Title>New Customer Pricing</Card.Title>
              <button type="button" aria-label="Close" onClick={() => setShow(false)}>
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </Card.Header>
            <Card.Body>
              <form onSubmit={save} className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <label className={label}>
                  Customer *
                  <select
                    required
                    className={field}
                    value={form.customer_id}
                    onChange={update('customer_id')}
                  >
                    <option value="">Select customer</option>
                    {(customersData?.items || []).map((customer) => (
                      <option key={customer.id} value={customer.id}>
                        {customer.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={label}>
                  Pricing Code *
                  <input required className={field} value={form.code} onChange={update('code')} />
                </label>
                <label className={label}>
                  Pricing Name *
                  <input required className={field} value={form.name} onChange={update('name')} />
                </label>
                <label className={label}>
                  Service Type *
                  <select
                    className={field}
                    value={form.service_type}
                    onChange={update('service_type')}
                  >
                    {services.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
                <label className={label}>
                  Calculation Basis *
                  <select
                    className={field}
                    value={form.calculation_basis}
                    onChange={update('calculation_basis')}
                  >
                    {bases.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
                <label className={label}>
                  Unit Rate *
                  <input
                    required
                    type="number"
                    min="0"
                    step="0.0001"
                    className={field}
                    value={form.unit_rate}
                    onChange={update('unit_rate')}
                  />
                </label>
                <label className={label}>
                  Minimum Charge
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className={field}
                    value={form.min_charge}
                    onChange={update('min_charge')}
                  />
                </label>
                <label className={label}>
                  Effective From *
                  <input
                    required
                    type="date"
                    className={field}
                    value={form.valid_from}
                    onChange={update('valid_from')}
                  />
                </label>
                <label className={label}>
                  Effective To
                  <input
                    type="date"
                    className={field}
                    value={form.valid_to}
                    onChange={update('valid_to')}
                  />
                </label>
                <div className="md:col-span-3 flex justify-end gap-3 border-t border-gray-100 pt-4">
                  <Button type="button" variant="secondary" onClick={() => setShow(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={create.isPending}>
                    Save Pricing
                  </Button>
                </div>
              </form>
            </Card.Body>
          </Card>
        </div>
      )}
      <DataTable
        columns={columns}
        data={cards}
        isLoading={isLoading}
        emptyTitle="No customer pricing found"
      />
    </div>
  );
}
