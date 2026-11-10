import React, { useMemo, useState } from 'react';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { ringsApi } from '../api/rings.api';
import { useRingsSales } from '../hooks/use-rings';

const thBase =
  'px-4 py-3 text-[11px] font-bold text-gray-700 uppercase tracking-wider whitespace-nowrap bg-gray-100/90 border-b border-gray-200 select-none';
const thLeft = `${thBase} text-left`;
const thRight = `${thBase} text-right`;
const thCenter = `${thBase} text-center`;

const tdBase = 'px-4 py-2.5 text-xs text-gray-800 whitespace-nowrap border-b border-gray-100';
const tdLeft = `${tdBase} text-left`;
const tdRight = `${tdBase} text-right font-mono tabular-nums`;
const tdCenter = `${tdBase} text-center`;

const formatCurrency = (val) => {
  if (val == null || val === '') return '—';
  const n = Number(val);
  return Number.isFinite(n)
    ? n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : String(val);
};

const formatQty = (val) => {
  if (val == null || val === '') return '—';
  const n = Number(val);
  return Number.isFinite(n)
    ? n.toLocaleString('en-IN', { maximumFractionDigits: 3 })
    : String(val);
};

const formatRate = (val) => {
  if (val == null || val === '') return '—';
  const n = Number(val);
  return Number.isFinite(n)
    ? n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
    : String(val);
};

const formatWeight = (val) => {
  if (val == null || val === '') return '—';
  const n = Number(val);
  return Number.isFinite(n) ? n.toFixed(3) : String(val);
};

const RingsSalesPage = () => {
  const [vendorId, setVendorId] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [workflow, setWorkflow] = useState('');
  const filters = useMemo(
    () => ({
      vendor_id: vendorId || undefined,
      customer_id: customerId || undefined,
      workflow: workflow || undefined,
    }),
    [vendorId, customerId, workflow]
  );
  const buyerQuery = useMemo(
    () => ({
      vendor_id: vendorId || undefined,
      workflow: workflow || undefined,
    }),
    [vendorId, workflow]
  );
  const { data, isLoading, error, refetch } = useRingsSales(filters);
  const { data: buyerSalesData } = useRingsSales(buyerQuery);
  const { data: vendorsData } = useVendors({ page_size: 200 });
  const rows = Array.isArray(data) ? data : [];
  const buyers = useMemo(() => {
    const map = new Map();
    (Array.isArray(buyerSalesData) ? buyerSalesData : []).forEach((row) => {
      if (row.customer_id && row.customer_name) {
        map.set(row.customer_id, row.customer_name);
      }
    });
    return [...map.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [buyerSalesData]);
  const vendors = useMemo(() => {
    return (vendorsData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [vendorsData]);
  const selectClass =
    'bg-white border border-gray-200 rounded-md px-3 py-1.5 text-xs font-medium focus:ring-2 focus:ring-primary-500 outline-none text-gray-700 shadow-2xs';

  const totals = useMemo(() => {
    return rows.reduce(
      (acc, r) => {
        acc.pallets += Number(r.pallet_count || 0);
        acc.qty += Number(r.quantity || 0);
        acc.basicValue += Number(r.basic_value || 0);
        acc.invValue += Number(r.invoice_value || r.basic_value || 0);
        acc.grossWeight += Number(r.line_gross_weight || r.gross_weight || 0);
        return acc;
      },
      { pallets: 0, qty: 0, basicValue: 0, invValue: 0, grossWeight: 0 }
    );
  }, [rows]);

  const downloadSales = async () => {
    try {
      await ringsApi.downloadSalesPdf(filters);
    } catch (err) {
      window.alert(err.message || 'Failed to download sales PDF');
    }
  };

  const downloadChallans = async () => {
    try {
      await ringsApi.downloadChallansPdf({
        vendor_id: vendorId || undefined,
        customer_id: customerId || undefined,
      });
    } catch (err) {
      window.alert(err.response?.data?.message || err.message || 'Failed to download challan PDF');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales Statement"
        breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Reports', to: '/reports' }, { label: 'Sales Report' }]}
        actions={(
          <>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                ringsApi
                  .downloadChallansXlsx({
                    vendor_id: vendorId || undefined,
                    customer_id: customerId || undefined,
                  })
                  .catch((err) => window.alert(err.message || 'Failed to download challan Excel'))
              }
            >
              Download SLN challans Excel
            </Button>
            <Button type="button" variant="secondary" onClick={downloadChallans}>
              Download SLN challans PDF
            </Button>
            <Button type="button" onClick={downloadSales}>
              Download sales PDF
            </Button>
          </>
        )}
      />
      <Card>
        <Card.Body className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-gray-100">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Filters:</span>
              <select className={selectClass} value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
                <option value="">All suppliers</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
              <select className={selectClass} value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
                <option value="">All buyers</option>
                {buyers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <select className={selectClass} value={workflow} onChange={(e) => setWorkflow(e.target.value)}>
                <option value="">All workflows</option>
                <option value="JOB_WORK">Job Work</option>
                <option value="DIRECT_INVOICE">Direct Invoice</option>
              </select>
            </div>
            <div className="text-xs text-gray-500 font-medium">
              Showing <span className="font-semibold text-gray-800">{rows.length}</span> record{rows.length !== 1 ? 's' : ''}
            </div>
          </div>
          {error && (
            <p className="text-sm text-red-600">
              {error.message} <button type="button" className="underline font-medium hover:text-red-700" onClick={() => refetch()}>Retry</button>
            </p>
          )}
          {isLoading ? (
            <div className="py-12 text-center text-sm text-gray-500">Loading sales records…</div>
          ) : (
            <div className="overflow-x-auto border border-gray-200 rounded-lg shadow-2xs bg-white">
              <table className="w-full text-xs min-w-[2400px] border-collapse">
                <thead className="sticky top-0 z-10 bg-gray-100 shadow-2xs">
                  <tr>
                    <th className={`${thLeft} min-w-[150px]`}>TYPES</th>
                    <th className={`${thLeft} min-w-[180px]`}>Supplier Challan / Invoice</th>
                    <th className={`${thLeft} min-w-[110px]`}>Challan Date</th>
                    <th className={`${thLeft} min-w-[160px]`}>Transporter</th>
                    <th className={`${thLeft} min-w-[220px]`}>Buyer Name</th>
                    <th className={`${thLeft} min-w-[190px]`}>Supp To Customer Invoice</th>
                    <th className={`${thLeft} min-w-[110px]`}>Inv Date</th>
                    <th className={`${thRight} min-w-[80px]`}>Pallets</th>
                    <th className={`${thRight} min-w-[110px]`}>QTY</th>
                    <th className={`${thRight} min-w-[90px]`}>Rate (₹)</th>
                    <th className={`${thRight} min-w-[120px]`}>Basic Value (₹)</th>
                    <th className={`${thRight} min-w-[90px]`}>IGST (₹)</th>
                    <th className={`${thRight} min-w-[120px]`}>Inv Value (₹)</th>
                    <th className={`${thLeft} min-w-[110px]`}>Dispatch Date</th>
                    <th className={`${thLeft} min-w-[120px]`}>PO NO</th>
                    <th className={`${thRight} min-w-[110px]`}>RING WT (kg)</th>
                    <th className={`${thRight} min-w-[110px]`}>Packing Wt (kg)</th>
                    <th className={`${thRight} min-w-[110px]`}>Gross Wt (kg)</th>
                    <th className={`${thCenter} min-w-[110px]`}>Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.map((row, idx) => (
                    <tr key={`${row.id}-${idx}`} className="hover:bg-primary-50/40 transition-colors odd:bg-white even:bg-gray-50/30">
                      <td className={`${tdLeft} font-semibold text-gray-900`}>{row.product_sku || '—'}</td>
                      <td className={`${tdLeft} font-mono`}>{row.supplier_document_number || '—'}</td>
                      <td className={tdLeft}>{row.challan_date || '—'}</td>
                      <td className={tdLeft}>{row.transporter_name || '—'}</td>
                      <td className={`${tdLeft} font-medium text-gray-900`}>{row.customer_name || '—'}</td>
                      <td className={`${tdLeft} font-mono`}>{row.supplier_customer_invoice_number || '—'}</td>
                      <td className={tdLeft}>{row.invoice_date || '—'}</td>
                      <td className={tdRight}>{row.pallet_count ?? 0}</td>
                      <td className={`${tdRight} font-semibold text-gray-900`}>{formatQty(row.quantity)}</td>
                      <td className={tdRight}>{formatRate(row.unit_rate)}</td>
                      <td className={tdRight}>{formatCurrency(row.basic_value)}</td>
                      <td className={tdRight}>0.00</td>
                      <td className={`${tdRight} font-semibold text-gray-900`}>{formatCurrency(row.invoice_value || row.basic_value)}</td>
                      <td className={tdLeft}>{row.dispatch_date || '—'}</td>
                      <td className={`${tdLeft} font-mono`}>{row.po_number || '—'}</td>
                      <td className={tdRight}>{formatWeight(row.per_ring_weight)}</td>
                      <td className={tdRight}>{formatWeight(row.packing_weight)}</td>
                      <td className={tdRight}>{formatWeight(row.line_gross_weight || row.gross_weight)}</td>
                      <td className={tdCenter}>
                        {row.workflow === 'JOB_WORK' ? (
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-primary-700 bg-primary-50 hover:bg-primary-100 hover:text-primary-800 border border-primary-200/60 rounded transition-colors shadow-2xs"
                            onClick={() => ringsApi.downloadChallanPdf(row.id).catch((e) => window.alert(e.message))}
                          >
                            Challan PDF
                          </button>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={19} className="py-12 text-center text-sm text-gray-400 font-medium">
                        No posted dispatches found matching current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
                {rows.length > 0 && (
                  <tfoot className="bg-gray-100/90 font-bold text-gray-900 border-t-2 border-gray-300">
                    <tr>
                      <td colSpan={7} className={`${tdLeft} font-bold text-gray-900 uppercase tracking-wider`}>
                        Total ({rows.length} {rows.length === 1 ? 'record' : 'records'})
                      </td>
                      <td className={tdRight}>{totals.pallets}</td>
                      <td className={`${tdRight} text-primary-900`}>{formatQty(totals.qty)}</td>
                      <td className={tdRight}>—</td>
                      <td className={tdRight}>₹ {formatCurrency(totals.basicValue)}</td>
                      <td className={tdRight}>₹ 0.00</td>
                      <td className={`${tdRight} text-primary-900`}>₹ {formatCurrency(totals.invValue)}</td>
                      <td colSpan={4} className={tdCenter}>—</td>
                      <td className={tdRight}>{formatWeight(totals.grossWeight)} kg</td>
                      <td className={tdCenter}></td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default RingsSalesPage;
