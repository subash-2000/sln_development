import React, { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Download } from 'lucide-react';
import { logisticsApi } from '../../logistics/api/logistics.api';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Loader from '../../../components/common/Loader';
import StatusBadge from '../../../components/ui/StatusBadge';
import { formatDateTime, formatQuantity } from '../../../utils/formatters';
import { useTransaction } from '../hooks/use-inventory';
import { parseInwardLineRemarks, parsePackagesFromRemarks } from '../../logistics/utils/inwardPackages';
import { useProducts } from '../../products/hooks/use-products';
import { useVendor, useVendors } from '../../vendors/hooks/use-vendors';
import { useLocations } from '../../locations/hooks/use-locations';

const TransactionDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const inwardContext = location.pathname.includes('/logistics/inward');
  const listPath = inwardContext ? '/logistics/inward' : '/inventory/transactions';
  const listLabel = inwardContext ? 'Inward' : 'Stock Transactions';
  const [packagesOpen, setPackagesOpen] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);

  const { data: tx, isLoading, error } = useTransaction(id);
  const { data: productsData } = useProducts({ page_size: 500 });
  const { data: vendorsData } = useVendors({ page_size: 500 });
  const { data: locationsData } = useLocations({ page_size: 500 });
  const partnerVendorId = tx?.partner_vendor_id;
  const { data: partnerVendor } = useVendor(partnerVendorId);

  const productById = useMemo(() => {
    const map = new Map();
    (productsData?.items || []).forEach((p) => map.set(p.id, p));
    return map;
  }, [productsData]);

  const vendorById = useMemo(() => {
    const map = new Map();
    (vendorsData?.items || []).forEach((v) => map.set(v.id, v));
    return map;
  }, [vendorsData]);

  const locationById = useMemo(() => {
    const map = new Map();
    (locationsData?.items || []).forEach((loc) => map.set(loc.id, loc));
    return map;
  }, [locationsData]);

  const lines = useMemo(() => {
    return (tx?.moves || []).map((line) => {
      const product = productById.get(line.product_id);
      const vendor = line.vendor_id ? vendorById.get(line.vendor_id) : null;
      const source = locationById.get(line.source_location_id);
      const destination = locationById.get(line.destination_location_id);
      const lineMeta = parseInwardLineRemarks(line.remarks);
      return {
        ...line,
        product_name: line.product_name || product?.name,
        sku: line.sku || product?.sku,
        uom_code: line.uom_code || product?.uom_code,
        vendor_name: line.vendor_name || vendor?.name,
        source_location_name: line.source_location_name || source?.name,
        destination_location_name: line.destination_location_name || destination?.name,
        part_number: lineMeta.part_number,
        line_packages: lineMeta.package_count,
        line_hsn: lineMeta.hsn_code,
        line_remark: lineMeta.line_remark,
      };
    });
  }, [tx, productById, vendorById, locationById]);

  const handleDownloadInvoicePdf = async () => {
    if (!tx?.id) return;
    setPdfLoading(true);
    try {
      await logisticsApi.inward.downloadInvoicePdf(tx.id);
    } catch (e) {
      window.alert(e?.message || 'Failed to download invoice PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  const packageMeta = useMemo(() => {
    if (!tx) return null;
    if (tx.package_lines?.length) {
      return { lines: tx.package_lines, total_packages: tx.total_packages };
    }
    return parsePackagesFromRemarks(tx.remarks);
  }, [tx?.package_lines, tx?.total_packages, tx?.remarks]);

  const inwardMovement = useMemo(() => {
    if (!tx?.moves?.length) return null;
    const first = tx.moves[0];
    const vendorId = tx.partner_vendor_id || first.vendor_id;
    const vendor =
      (partnerVendorId && partnerVendor?.id === partnerVendorId ? partnerVendor : null) ||
      (vendorId ? vendorById.get(vendorId) : null);
    const destination = locationById.get(first.destination_location_id);
    const supplierName =
      tx.partner_vendor_name || vendor?.name || first.vendor_name || null;
    const fromAddress =
      vendor?.address?.trim() ||
      vendor?.billing_address?.trim() ||
      vendor?.shipping_address?.trim() ||
      null;
    const destinationName =
      destination?.name || first.destination_location_name || null;
    const toLabel = [tx.warehouse_name, destinationName].filter(Boolean).join(' · ');
    return { supplierName, fromAddress, toLabel };
  }, [tx, partnerVendor, partnerVendorId, vendorById, locationById]);

  if (isLoading) return <Loader fullPage />;

  if (error || !tx) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-600">Unable to load transaction details.</p>
        <Button className="mt-4" onClick={() => navigate(listPath)}>Back to {listLabel}</Button>
      </Card>
    );
  }

  const partnerLabel =
    tx.partner_vendor_name || tx.partner_customer_name || '—';

  return (
    <div className="space-y-6">
      <PageHeader
        title={tx.transaction_number}
        description={`${tx.transaction_type} · ${tx.warehouse_name || 'Warehouse'}`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          inwardContext ? { label: 'Operations' } : { label: 'Inventory' },
          { label: listLabel, to: listPath },
          { label: tx.transaction_number },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            {inwardContext && tx.transaction_type === 'RECEIPT' && (
              <Button
                variant="secondary"
                leftIcon={<Download className="w-4 h-4" />}
                isLoading={pdfLoading}
                onClick={handleDownloadInvoicePdf}
              >
                Download invoice PDF
              </Button>
            )}
            <Button variant="outline" onClick={() => navigate(listPath)}>
              Back to list
            </Button>
          </div>
        }
      />

      <Card>
        <Card.Body className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          <div>
            <p className="text-gray-500">Status</p>
            <StatusBadge status={tx.status} />
          </div>
          <div>
            <p className="text-gray-500">Posted</p>
            <p className="font-medium">{formatDateTime(tx.created_at)}</p>
          </div>
          {inwardContext && inwardMovement ? (
            <>
              <div>
                <p className="text-gray-500">Supplier</p>
                <p className="font-medium">{inwardMovement.supplierName || '—'}</p>
              </div>
              <div className="sm:col-span-2">
                <p className="text-gray-500">From</p>
                <p className="font-medium whitespace-pre-line">
                  {inwardMovement.fromAddress || '—'}
                </p>
                {!inwardMovement.fromAddress && inwardMovement.supplierName && (
                  <p className="text-xs text-amber-700 mt-1">
                    Add address on the supplier master to show origin here.
                  </p>
                )}
              </div>
              <div className="sm:col-span-2 lg:col-span-1">
                <p className="text-gray-500">To</p>
                <p className="font-medium">{inwardMovement.toLabel || '—'}</p>
              </div>
            </>
          ) : (
            <div>
              <p className="text-gray-500">Supplier / Customer</p>
              <p className="font-medium">{partnerLabel}</p>
            </div>
          )}
          <div>
            <p className="text-gray-500">Source document</p>
            <p className="font-medium">
              {tx.reference_document_number || '—'}
              {tx.reference_document_type ? ` (${tx.reference_document_type})` : ''}
            </p>
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <p className="text-gray-500">Remarks</p>
            <p className="font-medium">{tx.remarks || '—'}</p>
          </div>
          <div>
            <p className="text-gray-500">Created By</p>
            <p className="font-medium">{tx.created_by || tx.created_by_name || '—'}</p>
          </div>
          <div>
            <p className="text-gray-500">Last Updated</p>
            <p className="font-medium">{tx.updated_at ? formatDateTime(tx.updated_at) : '—'}</p>
          </div>
          <div>
            <p className="text-gray-500">Updated By</p>
            <p className="font-medium">{tx.updated_by || '—'}</p>
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <h2 className="text-base font-semibold text-gray-900">Line items ({lines.length})</h2>
        </Card.Header>
        <Card.Body className="p-0 overflow-x-auto">
          <table className="w-max min-w-full text-sm table-auto">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs whitespace-nowrap">
              <tr>
                <th className="text-left px-4 py-3">Product</th>
                <th className="text-left px-4 py-3">SKU</th>
                {!inwardContext && (
                  <>
                    <th className="text-left px-4 py-3">Supplier</th>
                    <th className="text-left px-4 py-3">From</th>
                    <th className="text-left px-4 py-3">To</th>
                  </>
                )}
                <th className="text-left px-4 py-3">HSN</th>
                <th className="text-left px-4 py-3">Part No.</th>
                <th className="text-right px-4 py-3">Pkgs</th>
                <th className="text-left px-4 py-3">Lot / batch</th>
                <th className="text-right px-4 py-3">Qty</th>
                <th className="text-right px-4 py-3">Unit cost (₹)</th>
                {inwardContext && <th className="text-left px-4 py-3">Remark</th>}
              </tr>
            </thead>
            <tbody className="whitespace-nowrap">
              {lines.map((line) => (
                <tr key={line.id} className="border-t border-gray-100">
                  <td className="px-4 py-2">{line.product_name || '—'}</td>
                  <td className="px-4 py-2">{line.sku || '—'}</td>
                  {!inwardContext && (
                    <>
                      <td className="px-4 py-2">{line.vendor_name || '—'}</td>
                      <td className="px-4 py-2">{line.source_location_name || '—'}</td>
                      <td className="px-4 py-2">{line.destination_location_name || '—'}</td>
                    </>
                  )}
                  <td className="px-4 py-2 font-mono text-xs">{line.line_hsn || '—'}</td>
                  <td className="px-4 py-2 font-mono text-xs">{line.part_number || '—'}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{line.line_packages ?? '—'}</td>
                  <td className="px-4 py-2">
                    {(line.batch_number || line.lot_number) ? (
                      <Link
                        to={`/inventory/lots/${encodeURIComponent(line.batch_number || line.lot_number)}`}
                        className="text-primary-600 hover:underline font-medium"
                      >
                        {line.batch_number || line.lot_number}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {formatQuantity(line.quantity, line.uom_code)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{line.unit_cost ?? '—'}</td>
                  {inwardContext && (
                    <td className="px-4 py-2 max-w-xs whitespace-normal text-gray-700">
                      {line.line_remark || '—'}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {!lines.length && (
            <p className="text-center text-gray-500 py-8">No movement lines on this transaction.</p>
          )}
        </Card.Body>
      </Card>

      {packageMeta?.lines?.length > 0 && (
        <Card>
          <Card.Header className="py-3">
            <button
              type="button"
              onClick={() => setPackagesOpen((open) => !open)}
              className="flex w-full items-center justify-between gap-2 text-left"
              aria-expanded={packagesOpen}
            >
              <h2 className="text-base font-semibold text-gray-900">
                Part No. / packages
                {packageMeta.total_packages != null ? ` (total ${packageMeta.total_packages})` : ''}
              </h2>
              <span className="flex items-center gap-1 text-sm font-medium text-gray-500 shrink-0">
                {packagesOpen ? 'Hide' : 'Show'}
                {packagesOpen ? (
                  <ChevronUp className="w-4 h-4" aria-hidden />
                ) : (
                  <ChevronDown className="w-4 h-4" aria-hidden />
                )}
              </span>
            </button>
          </Card.Header>
          {packagesOpen && (
            <Card.Body className="p-0 overflow-x-auto border-t border-gray-100">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                  <tr>
                    <th className="text-left px-4 py-2">Part No.</th>
                    <th className="text-right px-4 py-2">No. of pkgs</th>
                  </tr>
                </thead>
                <tbody>
                  {packageMeta.lines.map((row) => (
                    <tr key={row.part_number} className="border-t border-gray-100">
                      <td className="px-4 py-2 font-mono">{row.part_number}</td>
                      <td className="px-4 py-2 text-right tabular-nums">{row.package_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card.Body>
          )}
        </Card>
      )}
    </div>
  );
};

export default TransactionDetailPage;
