import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Button from '../../../components/ui/Button';
import Card from '../../../components/ui/Card';
import { ringsApi } from '../api/rings.api';

const formatAmount = (n) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number.isFinite(Number(n)) ? Number(n) : 0
  );

const formatQty = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v)) return '—';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(v);
};

const formatWt = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v)) return '—';
  return v.toFixed(3);
};

const dash = (value) => {
  if (value === null || value === undefined) return '—';
  const text = String(value).trim();
  return text ? text : '—';
};

const formatHsnDisplay = (code) => {
  const s = String(code ?? '').trim();
  if (!s) return '—';
  const n = Number(s);
  if (Number.isFinite(n) && n > 0) return String(Math.trunc(n));
  return s.replace(/\.0+$/, '');
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const formatShortDate = (value) => {
  if (!value) return '—';
  const text = String(value).trim();
  const d = new Date(`${text.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dash(value);
  return `${String(d.getDate()).padStart(2, '0')}-${MONTHS[d.getMonth()]}-${String(d.getFullYear()).slice(-2)}`;
};

const workflowLabel = (workflow) => {
  if (workflow === 'JOB_WORK') return 'Job Work';
  if (workflow === 'DIRECT_INVOICE') return 'Direct Invoice';
  return dash(String(workflow || '').replaceAll('_', ' '));
};

const productLabel = (line) => {
  const sku = String(line?.product_sku || '').trim();
  const name = String(line?.product_name || '').trim();
  if (!name || !sku || name.toUpperCase() === sku.toUpperCase()) return sku || name || '—';
  return `${sku} — ${name}`;
};

const packingRatio = (packingDetail) => {
  const text = String(packingDetail || '').trim();
  if (!text) return '—';
  const match = text.match(/\(([^)]+)\)\s*$/);
  if (match?.[1]?.trim()) return match[1].trim();
  return text;
};

const Field = ({ label, children, className = '' }) => (
  <div className={className}>
    <p className="text-xs font-medium text-gray-500">{label}</p>
    <p className="mt-0.5 text-sm font-medium text-gray-900 break-words">{children ?? '—'}</p>
  </div>
);

const thBase =
  'px-2 py-2 text-[10px] font-semibold text-gray-400 uppercase leading-tight text-left whitespace-nowrap';
const thR = `${thBase} text-right`;
const tdBase = 'px-2 py-2.5 align-middle text-sm text-gray-800 whitespace-nowrap';
const tdR = `${tdBase} text-right tabular-nums whitespace-nowrap`;

const RingsDocumentDetailPage = () => {
  const { id } = useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ['rings-document', id],
    queryFn: () => ringsApi.getDocument(id),
    enabled: !!id,
  });

  if (isLoading) return <p className="p-6 text-sm text-gray-500">Loading…</p>;
  if (error || !data) return <p className="p-6 text-sm text-red-600">{error?.message || 'Not found'}</p>;

  const isInward = data.document_type === 'INWARD';
  const isPick = data.document_type === 'PICK' || data.document_type === 'OUTWARD';
  const isDirect = data.workflow === 'DIRECT_INVOICE';
  const lines = data.lines || [];
  const lineRows = lines.map((line) => {
    const taxable = Number(line.basic_value ?? (Number(line.quantity || 0) * Number(line.unit_rate || 0)));
    const gstPct = Number(line.gst_percent || 0);
    const gst = taxable * (gstPct / 100);
    return { line, taxable, gstPct, gst, total: taxable + gst };
  });
  const summary = lineRows.reduce(
    (acc, row) => {
      acc.taxable += row.taxable;
      acc.gst += row.gst;
      acc.grand += row.total;
      return acc;
    },
    { taxable: 0, gst: 0, grand: 0 }
  );
  const weightSummary = lines.reduce(
    (acc, line) => {
      const qty = Number(line.quantity || 0);
      const ring = Number(line.per_ring_weight || 0);
      const pack = Number(line.packing_weight || 0);
      const gross = qty * ring;
      acc.gross += gross;
      acc.total += gross + pack;
      return acc;
    },
    { gross: 0, total: 0 }
  );

  const uniqueSupplierNames = Array.from(new Set(lines.map((l) => l.vendor_name).filter(Boolean)));
  const displaySupplier = uniqueSupplierNames.length > 1
    ? `Multiple (${uniqueSupplierNames.length} suppliers)`
    : (data.vendor_name || uniqueSupplierNames[0] || '—');

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.document_number}
        description={`${data.document_type} · ${workflowLabel(data.workflow)} · ${data.status}`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Operations', to: '/rings/inward' },
          { label: isInward ? 'Inward' : data.document_type, to: isInward ? '/rings/inward' : undefined },
          { label: data.document_number },
        ]}
        actions={(
          <>
            {(data.document_type === 'PICK' || data.document_type === 'OUTWARD') && (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => ringsApi.downloadPickXlsx(data.id).catch((e) => window.alert(e.message))}
                >
                  Download pick Excel
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => ringsApi.downloadPickPdf(data.id).catch((e) => window.alert(e.message))}
                >
                  Download pick PDF
                </Button>
              </>
            )}
            {data.workflow === 'JOB_WORK' && (data.document_type === 'OUTWARD' || data.status === 'POSTED') && data.document_type !== 'INWARD' && (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => ringsApi.downloadChallanXlsx(data.id).catch((e) => window.alert(e.message))}
                >
                  Download SLN challan Excel
                </Button>
                <Button
                  type="button"
                  onClick={() => ringsApi.downloadChallanPdf(data.id).catch((e) => window.alert(e.message))}
                >
                  Download SLN challan PDF
                </Button>
              </>
            )}
          </>
        )}
      />

      <Card>
        <Card.Header className="py-3">
          <h3 className="text-base font-medium">Header Information</h3>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">
          <Field label="Warehouse">{dash(data.warehouse_name)}</Field>
          <Field label="Supplier">{displaySupplier}</Field>
          <Field label="Transaction Date">{dash(data.supplier_document_date)}</Field>
          <Field label="Reference Type">{workflowLabel(data.workflow)}</Field>
          <Field label={isDirect ? 'Invoice Number' : 'Primary reference'}>
            {dash(data.supplier_document_number)}
          </Field>
          <Field label="Challan Date">{formatShortDate(data.supplier_document_date)}</Field>
          <Field label="Reference Date">{formatShortDate(data.reference_date)}</Field>
          <Field label="Transporter">{dash(data.transporter_name)}</Field>
          <Field label="Vehicle">{dash(data.vehicle_number)}</Field>
          <Field label="LR / GR">{dash(data.lr_number)}</Field>
          <Field label="LR Date">{dash(data.lr_date)}</Field>
          <Field label="Received Date">{dash(data.received_date)}</Field>
          <Field label="PO Number">{dash(data.po_number)}</Field>
          <Field label="Packing Weight (kg)">{formatWt(data.packing_weight)}</Field>
          {!isInward && <Field label="Buyer">{dash(data.customer_name)}</Field>}
          {!isInward && <Field label="SLN challan">{dash(data.sln_challan_number)}</Field>}
          <Field label="Remarks" className="md:col-span-3">{dash(data.remarks)}</Field>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="py-3">
          <h3 className="text-base font-medium">Items</h3>
        </Card.Header>
        <Card.Body className="py-2 px-3">
          <div className="overflow-x-auto -mx-1 px-1">
            <table className={`w-full border-separate border-spacing-y-1 ${isPick ? 'min-w-[130rem]' : 'min-w-[100rem]'}`}>
              {isPick && (
                <colgroup>
                  <col className="w-[12rem]" />
                  <col className="w-[13rem]" />
                  <col className="w-[7rem]" />
                  <col className="w-[9rem]" />
                  <col className="w-[7rem]" />
                  <col className="w-[7rem]" />
                  <col className="w-[8.5rem]" />
                  <col className="w-[7rem]" />
                  <col className="w-[14rem]" />
                  <col className="w-[14rem]" />
                  <col className="w-[10rem]" />
                  <col className="w-[18rem]" />
                  <col className="w-[9rem]" />
                  <col className="w-[8rem]" />
                  <col className="w-[8rem]" />
                </colgroup>
              )}
              <thead>
                <tr>
                  {isPick ? (
                    <>
                      <th className={thBase}>Product</th>
                      <th className={thBase}>Invoice Number</th>
                      <th className={thBase}>DATE</th>
                      <th className={thBase}>TRANSPORTER</th>
                      <th className={thBase}>REC.DATE</th>
                      <th className={thR}>Total Pallets</th>
                      <th className={thBase}>Per Pallet * Qty</th>
                      <th className={thR}>Total QTY</th>
                      <th className={thBase}>Supplier Name</th>
                      <th className={thBase}>Buyer Name</th>
                      <th className={thBase}>Purchase Order Number</th>
                      <th className={thBase}>Heat Number</th>
                      <th className={thR}>Per Ring Weight</th>
                      <th className={thR}>Packing Weight</th>
                      <th className={thR}>Gross Weight</th>
                      <th className={thR}>Total Weight</th>
                    </>
                  ) : (
                    <>
                      <th className={thBase}>Product</th>
                      <th className={thBase}>HSN</th>
                      <th className={thBase}>Challan No</th>
                      <th className={thBase}>Ref No</th>
                      <th className={thBase}>Ratio</th>
                      <th className={thR}>Pallets</th>
                      <th className={thR}>Qty / Pallet</th>
                      <th className={thR}>Boxes</th>
                      <th className={thR}>Qty / Box</th>
                      <th className={thR}>Short Qty</th>
                      <th className={thR}>Qty</th>
                      <th className={thBase}>Heat No.</th>
                      <th className={thBase}>Part No</th>
                      <th className={thBase}>UOM</th>
                      <th className={thR}>Rate</th>
                      <th className={thR}>GST%</th>
                      <th className={thR}>Taxable ₹</th>
                      <th className={thR}>Ring Wt</th>
                      <th className={thR}>Packing Wt</th>
                      <th className={thR}>Gross Wt</th>
                      <th className={thR}>Total Wt</th>
                      <th className={thR}>Total ₹</th>
                      <th className={thBase}>Remark</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {lineRows.map(({ line, taxable, gstPct, total }) => {
                  const remarkText = String(line.remarks || '').trim();
                  const pallets = Number(line.pallet_count || 0);
                  const per = Number(line.qty_per_pallet || 0);
                  const palletText = pallets && per
                    ? `${pallets}*${Number.isInteger(per) ? per : per}`
                    : dash(line.packing_detail);
                  const pack = Number(line.packing_weight || 0);
                  const ring = Number(line.per_ring_weight || 0);
                  const qty = Number(line.quantity || 0);
                  const gross = qty * ring;
                  const totalWt = gross + pack;
                  if (isPick) {
                    return (
                      <tr key={line.id} className="bg-gray-50/80">
                        <td className={`${tdBase} min-w-[10rem]`}>{productLabel(line)}</td>
                        <td className={tdBase}>{dash(line.source_document_number || data.supplier_document_number)}</td>
                        <td className={tdBase}>{formatShortDate(line.source_document_date || data.supplier_document_date)}</td>
                        <td className={tdBase}>{dash(line.transporter_name || data.transporter_name)}</td>
                        <td className={tdBase}>{formatShortDate(line.received_date || data.received_date)}</td>
                        <td className={tdR}>{formatQty(line.pallet_count)}</td>
                        <td className={tdBase}>{palletText}</td>
                        <td className={tdR}>{formatQty(line.quantity)}</td>
                        <td className={tdBase}>{dash(line.vendor_name || data.vendor_name)}</td>
                        <td className={tdBase}>{dash(data.customer_name)}</td>
                        <td className={tdBase}>{dash(data.po_number)}</td>
                        <td className={`${tdBase} font-medium`}>{dash(line.heat_number)}</td>
                        <td className={tdR}>{formatWt(line.per_ring_weight)}</td>
                        <td className={tdR}>{formatWt(pack)}</td>
                        <td className={`${tdR} font-medium`}>{formatWt(gross)}</td>
                        <td className={`${tdR} font-semibold text-gray-900`}>{formatWt(totalWt)}</td>
                      </tr>
                    );
                  }
                  return (
                    <tr key={line.id} className="bg-gray-50/80">
                      <td className={`${tdBase} min-w-[14rem]`}>{productLabel(line)}</td>
                      <td className={`${tdBase} font-mono text-xs text-gray-600`}>
                        {formatHsnDisplay(line.hsn_code)}
                      </td>
                      <td className={tdBase}>{dash(line.source_document_number)}</td>
                      <td className={tdBase}>{dash(line.reference_number)}</td>
                      <td className={`${tdBase} whitespace-nowrap`}>
                        {String(line.packing_ratio || '').trim() || packingRatio(line.packing_detail)}
                      </td>
                      <td className={tdR}>{formatQty(line.pallet_count)}</td>
                      <td className={tdR}>{formatQty(line.qty_per_pallet)}</td>
                      <td className={tdR}>{formatQty(line.box_count)}</td>
                      <td className={tdR}>{formatQty(line.qty_per_box)}</td>
                      <td className={tdR}>
                        {line.short_quantity != null && line.short_quantity !== ''
                          ? formatQty(line.short_quantity)
                          : '—'}
                      </td>
                      <td className={tdR}>{formatQty(line.quantity)}</td>
                      <td className={`${tdBase} whitespace-nowrap min-w-[8.5rem] font-medium`}>
                        {dash(line.heat_number)}
                      </td>
                      <td className={`${tdBase} font-mono text-xs`}>{dash(line.part_number)}</td>
                      <td className={`${tdBase} text-center`}>{dash(line.uom_code)}</td>
                      <td className={tdR}>{formatAmount(line.unit_rate)}</td>
                      <td className={tdR}>{formatQty(gstPct)}</td>
                      <td className={tdR}>{formatAmount(taxable)}</td>
                      <td className={tdR}>{formatWt(line.per_ring_weight)}</td>
                      <td className={tdR}>{formatWt(pack)}</td>
                      <td className={`${tdR} font-medium`}>{formatWt(gross)}</td>
                      <td className={`${tdR} font-semibold text-gray-900`}>{formatWt(totalWt)}</td>
                      <td className={`${tdR} font-medium text-gray-900`}>{formatAmount(total)}</td>
                      <td className={`${tdBase} min-w-[8rem]`}>
                        {remarkText ? (
                          <span title={remarkText}>
                            <span className="font-medium">Yes</span>
                            <span className="block text-xs text-gray-500 truncate max-w-[12rem]">{remarkText}</span>
                          </span>
                        ) : (
                          'No'
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:justify-end gap-3 text-sm">
            <div className="space-y-1 sm:text-right min-w-[220px]">
              <div className="flex justify-between sm:justify-end gap-4 text-gray-600">
                <span>Taxable value (₹)</span>
                <span className="tabular-nums">{formatAmount(summary.taxable)}</span>
              </div>
              <div className="flex justify-between sm:justify-end gap-4 text-gray-600">
                <span>GST (₹)</span>
                <span className="tabular-nums">{formatAmount(summary.gst)}</span>
              </div>
              <div className="flex justify-between sm:justify-end gap-4 font-semibold text-gray-900">
                <span>Total (₹)</span>
                <span className="tabular-nums">{formatAmount(summary.grand)}</span>
              </div>
              <div className="flex justify-between sm:justify-end gap-4 text-xs text-gray-500 pt-1">
                <span>Gross weight (kg)</span>
                <span className="tabular-nums">
                  {formatWt(isInward || isPick ? weightSummary.gross : data.gross_weight)}
                </span>
              </div>
              {(isInward || isPick) && (
                <div className="flex justify-between sm:justify-end gap-4 text-xs font-medium text-gray-700">
                  <span>Total weight (kg)</span>
                  <span className="tabular-nums">
                    {formatWt(weightSummary.total || data.gross_weight)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default RingsDocumentDetailPage;
