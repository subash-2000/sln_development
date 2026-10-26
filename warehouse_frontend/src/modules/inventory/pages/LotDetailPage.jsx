import React, { useMemo } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Loader from '../../../components/common/Loader';
import { formatDateTime, formatQuantity } from '../../../utils/formatters';
import { inventoryApi } from '../api/inventory.api';

const formatAmount = (n) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number(n) || 0
  );

const LotDetailPage = () => {
  const { lotNumber: lotNumberParam } = useParams();
  const navigate = useNavigate();
  const lotNumber = decodeURIComponent(lotNumberParam || '');

  const { data: stockData, isLoading: stockLoading } = useQuery({
    queryKey: ['lot-stock', lotNumber],
    queryFn: () => inventoryApi.stock({ batch_number: lotNumber, page_size: 100 }),
    enabled: Boolean(lotNumber),
  });

  const { data: ledgerData, isLoading: ledgerLoading } = useQuery({
    queryKey: ['lot-ledger', lotNumber],
    queryFn: () => inventoryApi.ledger({ batch_number: lotNumber, page_size: 100 }),
    enabled: Boolean(lotNumber),
  });

  const stockRows = stockData?.items || [];
  const ledgerRows = ledgerData?.items || [];

  const receiptTxIds = useMemo(() => {
    const ids = new Set();
    ledgerRows.forEach((row) => {
      if (row.transaction_id && row.quantity_delta > 0) ids.add(row.transaction_id);
    });
    return [...ids];
  }, [ledgerRows]);

  if (!lotNumber) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-600">Invalid lot number.</p>
        <Button className="mt-4" onClick={() => navigate('/inventory/stock')}>Back to stock</Button>
      </Card>
    );
  }

  if (stockLoading && ledgerLoading) return <Loader fullPage />;

  return (
    <div className="space-y-4">
      <PageHeader
        title={lotNumber}
        description="Lot / batch stock and movement history (saved when you post inward)."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Inventory' },
          { label: 'Stock', to: '/inventory/stock' },
          { label: lotNumber },
        ]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate('/inventory/stock')}>
            Back to stock
          </Button>
        }
      />

      {receiptTxIds.length > 0 && (
        <Card>
          <Card.Body className="py-3 text-sm">
            <p className="text-gray-500 mb-1">Created from inward receipt</p>
            <div className="flex flex-wrap gap-2">
              {receiptTxIds.map((id) => (
                <Link
                  key={id}
                  to={`/logistics/inward/${id}`}
                  className="text-primary-600 hover:underline font-medium"
                >
                  View inward transaction
                </Link>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}

      <Card>
        <Card.Header className="py-3">
          <h2 className="text-base font-semibold">Current stock for this lot</h2>
        </Card.Header>
        <Card.Body className="p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="text-left px-4 py-2">Product</th>
                <th className="text-left px-4 py-2">SKU</th>
                <th className="text-left px-4 py-2">Warehouse</th>
                <th className="text-left px-4 py-2">Location</th>
                <th className="text-right px-4 py-2">On hand</th>
                <th className="text-right px-4 py-2">Available</th>
              </tr>
            </thead>
            <tbody>
              {stockRows.map((row) => (
                <tr key={row.id} className="border-t border-gray-100">
                  <td className="px-4 py-2">{row.product_name}</td>
                  <td className="px-4 py-2">{row.sku}</td>
                  <td className="px-4 py-2">{row.warehouse_name}</td>
                  <td className="px-4 py-2">{row.location_name}</td>
                  <td className="px-4 py-2 text-right">
                    {formatQuantity(row.quantity_on_hand, row.uom_code)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {formatQuantity(row.quantity_available, row.uom_code)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!stockRows.length && (
            <p className="text-center text-gray-500 py-6 text-sm">
              No stock on hand for this lot. Post inward with this lot #, or check the number.
            </p>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="py-3">
          <h2 className="text-base font-semibold">Lot movement history</h2>
        </Card.Header>
        <Card.Body className="p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="text-left px-4 py-2">Date</th>
                <th className="text-left px-4 py-2">Product</th>
                <th className="text-right px-4 py-2">Qty change</th>
                <th className="text-right px-4 py-2">Unit cost (₹)</th>
                <th className="text-left px-4 py-2">Transaction</th>
              </tr>
            </thead>
            <tbody>
              {ledgerRows.map((row) => (
                <tr key={row.id} className="border-t border-gray-100">
                  <td className="px-4 py-2">{formatDateTime(row.posting_date)}</td>
                  <td className="px-4 py-2">{row.product_name || row.sku}</td>
                  <td className="px-4 py-2 text-right">
                    {formatQuantity(row.quantity_delta, row.uom_code)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {row.unit_cost != null ? formatAmount(row.unit_cost) : '—'}
                  </td>
                  <td className="px-4 py-2">
                    {row.transaction_id ? (
                      <Link
                        to={`/inventory/transactions/${row.transaction_id}`}
                        className="text-primary-600 hover:underline"
                      >
                        {row.reference || 'View receipt'}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!ledgerRows.length && (
            <p className="text-center text-gray-500 py-6 text-sm">No ledger entries for this lot yet.</p>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default LotDetailPage;
