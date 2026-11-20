import React, { useMemo, useState } from 'react';
import { Plus, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import DataTable from '../../../components/tables/DataTable';
import RowActions from '../../../components/tables/RowActions';
import { useVendors } from '../../vendors/hooks/use-vendors';
import {
  useCreditDebitActions,
  useCreditDebitNotes,
  useCreditDebitSummary,
} from '../hooks/use-credit-debit';
import { invoicingApi } from '../../invoicing/api/invoicing.api';

const today = () => new Date().toISOString().slice(0, 10);
const blank = () => ({
  customer_id: null,
  vendor_id: '',
  invoice_id: '',
  note_type: 'CREDIT',
  note_number: '',
  note_date: today(),
  amount: '',
  reason: '',
  description: '',
  remarks: '',
});
const money = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value || 0));
const field =
  'w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all duration-200';
const formLabel = 'block text-sm font-medium text-gray-700 space-y-1.5';

export default function CreditDebitPage() {
  const [vendorId, setVendorId] = useState('');
  const [type, setType] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [form, setForm] = useState(null);
  const [editing, setEditing] = useState(null);
  const params = useMemo(
    () => ({
      page_size: 100,
      vendor_id: vendorId || undefined,
      note_type: type || undefined,
      status: status || undefined,
      search: search || undefined,
    }),
    [vendorId, type, status, search]
  );
  const { data, isLoading } = useCreditDebitNotes(params);
  const { data: summary } = useCreditDebitSummary({ vendor_id: vendorId || undefined });
  const { data: vendorData } = useVendors({ page_size: 200, status: 'ACTIVE' });
  const { data: invoiceData } = useQuery({
    queryKey: ['credit-debit-invoices', form?.vendor_id],
    queryFn: () => invoicingApi.list({ page_size: 200, vendor_id: form?.vendor_id }),
    enabled: !!form?.vendor_id,
  });
  const actions = useCreditDebitActions();
  const suppliers = vendorData?.items || [];
  const columns = useMemo(
    () => [
      { key: 'note_date', label: 'Date', type: 'date', widthClass: 'w-32' },
      { key: 'vendor_name', label: 'Supplier' },
      { key: 'note_type', label: 'Type', widthClass: 'w-28' },
      { key: 'note_number', label: 'Note No.', widthClass: 'w-36' },
      { key: 'invoice_number', label: 'Invoice', widthClass: 'w-36' },
      { key: 'amount', label: 'Amount', type: 'currency', widthClass: 'w-36' },
      { key: 'reason', label: 'Reason' },
      { key: 'status', label: 'Status', type: 'status', widthClass: 'w-32' },
    ],
    []
  );

  const save = async (e) => {
    e.preventDefault();
    const payload = { ...form, amount: Number(form.amount), invoice_id: form.invoice_id || null };
    try {
      if (editing) await actions.update.mutateAsync({ id: editing, data: payload });
      else await actions.create.mutateAsync(payload);
      setForm(null);
      setEditing(null);
    } catch (err) {
      window.alert(err.response?.data?.message || err.message);
    }
  };
  const edit = (row) => {
    setEditing(row.id);
    setForm({
      customer_id: null,
      vendor_id: row.vendor_id || '',
      invoice_id: row.invoice_id || '',
      note_type: row.note_type,
      note_number: row.note_number,
      note_date: row.note_date,
      amount: row.amount,
      reason: row.reason,
      description: row.description || '',
      remarks: row.remarks || '',
    });
  };
  const exportCsv = () => {
    const rows = data?.items || [];
    const csv = [
      ['Date', 'Supplier', 'Type', 'Note Number', 'Invoice', 'Amount', 'Reason', 'Status'],
      ...rows.map((r) => [
        r.note_date,
        r.vendor_name,
        r.note_type,
        r.note_number,
        r.invoice_number || '',
        r.amount,
        r.reason,
        r.status,
      ]),
    ]
      .map((row) => row.map((v) => `"${String(v ?? '').replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'supplier-credit-debit-notes.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const confirm = async (row) => {
    if (!window.confirm(`Confirm ${row.note_number}? Financial fields cannot be edited afterward.`))
      return;
    try {
      await actions.confirm.mutateAsync(row.id);
    } catch (e) {
      window.alert(e.response?.data?.message || e.message);
    }
  };
  const cancel = async (row) => {
    const reason = window.prompt(`Cancellation reason for ${row.note_number}`);
    if (!reason) return;
    try {
      await actions.cancel.mutateAsync({ id: row.id, reason });
    } catch (e) {
      window.alert(e.response?.data?.message || e.message);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Credit & Debit Notes"
        description="Manual supplier adjustments with controlled confirmation and cancellation."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Finance' },
          { label: 'Credit & Debit Notes' },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={exportCsv}>
              Export CSV
            </Button>
            <Button
              onClick={() => {
                setEditing(null);
                setForm(blank());
              }}
            >
              <Plus className="w-4 h-4 mr-1" />
              New Note
            </Button>
          </div>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          ['Confirmed Credit', summary?.total_credit, 'text-emerald-700'],
          ['Confirmed Debit', summary?.total_debit, 'text-rose-700'],
          ['Net Adjustment', summary?.net_adjustment, 'text-blue-700'],
          [
            'Draft / Cancelled',
            `${summary?.draft_count || 0} / ${summary?.cancelled_count || 0}`,
            'text-gray-900',
          ],
        ].map(([label, value, cls]) => (
          <Card key={label} className="p-4">
            <div className="text-xs text-gray-500">{label}</div>
            <div className={`text-2xl font-bold mt-1 ${cls}`}>
              {typeof value === 'string' && value.includes('/') ? value : money(value)}
            </div>
          </Card>
        ))}
      </div>
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <select className={field} value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
            <option value="">All Suppliers</option>
            {suppliers.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
          <select className={field} value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">Credit & Debit</option>
            <option value="CREDIT">Credit Notes</option>
            <option value="DEBIT">Debit Notes</option>
          </select>
          <select className={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All Statuses</option>
            <option>DRAFT</option>
            <option>CONFIRMED</option>
            <option>CANCELLED</option>
          </select>
          <input
            className={field}
            placeholder="Search note number or reason"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </Card>
      {form && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={editing ? 'Edit Draft Note' : 'New Credit/Debit Note'}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              setForm(null);
              setEditing(null);
            }
          }}
        >
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-xl">
            <Card.Header className="sticky top-0 z-10 flex items-center justify-between bg-white">
              <h3 className="text-lg font-semibold text-gray-900">
                {editing ? 'Edit Draft Note' : 'New Credit/Debit Note'}
              </h3>
              <button
                type="button"
                aria-label="Close"
                onClick={() => {
                  setForm(null);
                  setEditing(null);
                }}
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </Card.Header>
            <Card.Body>
              <form onSubmit={save} className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <label className={formLabel}>
                  Supplier *
                  <select
                    required
                    className={`${field} mt-1`}
                    value={form.vendor_id}
                    onChange={(e) =>
                      setForm({ ...form, vendor_id: e.target.value, invoice_id: '' })
                    }
                  >
                    <option value="">Select supplier</option>
                    {suppliers.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={formLabel}>
                  Note Type *
                  <select
                    className={`${field} mt-1`}
                    value={form.note_type}
                    onChange={(e) => setForm({ ...form, note_type: e.target.value })}
                  >
                    <option value="CREDIT">Credit Note</option>
                    <option value="DEBIT">Debit Note</option>
                  </select>
                </label>
                <label className={formLabel}>
                  Invoice (optional)
                  <select
                    className={`${field} mt-1`}
                    value={form.invoice_id}
                    onChange={(e) => setForm({ ...form, invoice_id: e.target.value })}
                  >
                    <option value="">Unlinked supplier note</option>
                    {(invoiceData?.items || []).map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.invoice_number} · {money(i.total_amount)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={formLabel}>
                  Note Number *
                  <input
                    required
                    className={`${field} mt-1`}
                    value={form.note_number}
                    onChange={(e) => setForm({ ...form, note_number: e.target.value })}
                  />
                </label>
                <label className={formLabel}>
                  Note Date *
                  <input
                    required
                    type="date"
                    className={`${field} mt-1`}
                    value={form.note_date}
                    onChange={(e) => setForm({ ...form, note_date: e.target.value })}
                  />
                </label>
                <label className={formLabel}>
                  Amount *
                  <input
                    required
                    min="0.01"
                    step="0.01"
                    type="number"
                    className={`${field} mt-1`}
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  />
                </label>
                <label className={formLabel}>
                  Reason *
                  <input
                    required
                    className={`${field} mt-1`}
                    value={form.reason}
                    onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  />
                </label>
                <label className={`${formLabel} md:col-span-2`}>
                  Description
                  <textarea
                    className={`${field} min-h-20 resize-y`}
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </label>
                <label className={formLabel}>
                  Remarks
                  <textarea
                    className={`${field} min-h-20 resize-y`}
                    value={form.remarks}
                    onChange={(e) => setForm({ ...form, remarks: e.target.value })}
                  />
                </label>
                <div className="md:col-span-3 flex justify-end gap-3 border-t border-gray-100 pt-4 mt-1">
                  <Button type="button" variant="secondary" onClick={() => setForm(null)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    isLoading={actions.create.isPending || actions.update.isPending}
                  >
                    Save Draft
                  </Button>
                </div>
              </form>
            </Card.Body>
          </Card>
        </div>
      )}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                {[
                  'Date',
                  'Supplier',
                  'Type',
                  'Note No.',
                  'Invoice',
                  'Amount',
                  'Reason',
                  'Status',
                  'Actions',
                ].map((h) => (
                  <th key={h} className="px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="9" className="p-8 text-center">
                    Loading…
                  </td>
                </tr>
              ) : (
                (data?.items || []).map((row) => (
                  <tr key={row.id} className="border-t">
                    <td className="px-4 py-3">{row.note_date}</td>
                    <td className="px-4 py-3">{row.vendor_name || '—'}</td>
                    <td className="px-4 py-3 font-medium">{row.note_type}</td>
                    <td className="px-4 py-3">{row.note_number}</td>
                    <td className="px-4 py-3">{row.invoice_number || '—'}</td>
                    <td className="px-4 py-3 font-semibold">{money(row.amount)}</td>
                    <td className="px-4 py-3">{row.reason}</td>
                    <td className="px-4 py-3">{row.status}</td>
                    <td className="px-4 py-3 whitespace-nowrap space-x-2">
                      {row.status === 'DRAFT' && (
                        <>
                          <button className="text-blue-600" onClick={() => edit(row)}>
                            Edit
                          </button>
                          <button className="text-emerald-600" onClick={() => confirm(row)}>
                            Confirm
                          </button>
                        </>
                      )}{' '}
                      {row.status !== 'CANCELLED' && (
                        <button className="text-red-600" onClick={() => cancel(row)}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
              {!isLoading && !(data?.items || []).length && (
                <tr>
                  <td colSpan="9" className="p-8 text-center text-gray-500">
                    No Credit/Debit Notes found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
