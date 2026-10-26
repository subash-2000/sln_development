import React, { useMemo, useState } from 'react';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { ringsApi } from '../api/rings.api';
import { useRingsSales } from '../hooks/use-rings';

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
  const { data: buyerSource } = useRingsSales(buyerQuery);
  const { data: vendorsData } = useVendors({ page_size: 200 });
  const rows = Array.isArray(data) ? data : [];
  const buyers = useMemo(() => {
    const map = new Map();
    (Array.isArray(buyerSource) ? buyerSource : []).forEach((row) => {
      if (row.customer_id && row.customer_name) {
        map.set(row.customer_id, row.customer_name);
      }
    });
    return [...map.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [buyerSource]);
  const selectClass =
    'bg-white border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none';

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
        breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Operations' }, { label: 'Sales Report' }]}
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
          <div className="flex flex-wrap gap-3">
            <select className={selectClass} value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
              <option value="">All suppliers</option>
              {(vendorsData?.items || []).map((v) => (
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
          {error && (
            <p className="text-sm text-red-600">
              {error.message} <button type="button" className="underline" onClick={() => refetch()}>Retry</button>
            </p>
          )}
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs min-w-[1400px]">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2">TYPES</th>
                    <th>Supplier Challan / Invoice</th>
                    <th>Challan Date</th>
                    <th>Transporter</th>
                    <th>Buyer Name</th>
                    <th>Supp To Customer Invoice</th>
                    <th>Inv Date</th>
                    <th>Pallets</th>
                    <th>QTY</th>
                    <th>Rate</th>
                    <th>Basic Value</th>
                    <th>IGST</th>
                    <th>Inv Value</th>
                    <th>Dispatch Date</th>
                    <th>PO NO</th>
                    <th>RING WT</th>
                    <th>Packing Wt</th>
                    <th>Gross Wt</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, idx) => (
                    <tr key={`${row.id}-${idx}`} className="border-b border-gray-50">
                      <td className="py-2">{row.product_sku}</td>
                      <td>{row.supplier_document_number}</td>
                      <td>{row.challan_date || '—'}</td>
                      <td>{row.transporter_name || '—'}</td>
                      <td>{row.customer_name || '—'}</td>
                      <td>{row.supplier_customer_invoice_number || '—'}</td>
                      <td>{row.invoice_date || '—'}</td>
                      <td>{row.pallet_count}</td>
                      <td>{row.quantity}</td>
                      <td>{row.unit_rate}</td>
                      <td>{row.basic_value}</td>
                      <td>0.00</td>
                      <td>{row.invoice_value || row.basic_value}</td>
                      <td>{row.dispatch_date || '—'}</td>
                      <td>{row.po_number || '—'}</td>
                      <td>{row.per_ring_weight}</td>
                      <td>{row.packing_weight}</td>
                      <td>{row.line_gross_weight || row.gross_weight}</td>
                      <td>
                        {row.workflow === 'JOB_WORK' && (
                          <button
                            type="button"
                            className="text-primary-700 underline cursor-pointer hover:text-primary-800"
                            onClick={() => ringsApi.downloadChallanPdf(row.id).catch((e) => window.alert(e.message))}
                          >
                            Challan PDF
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={19} className="py-6 text-center text-gray-400">
                        No posted dispatches yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default RingsSalesPage;
