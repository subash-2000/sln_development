import React, { useState } from 'react';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Input from '../../../components/ui/Input';
import { useRingsDayClose, useRingsStock } from '../hooks/use-rings';

const today = () => new Date().toISOString().slice(0, 10);

const RingsStockPage = () => {
  const [asOf, setAsOf] = useState(today());
  const { data: stock, isLoading, error, refetch } = useRingsStock();
  const { data: closing } = useRingsDayClose({ as_of: asOf }, !!asOf);
  const rows = Array.isArray(stock) ? stock : [];
  const closeRows = Array.isArray(closing) ? closing : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stock Closing"
        description="Balances are tracked by supplier + product type + heat number. Closing = opening + inward − outward."
        breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Operations' }, { label: 'Stock Closing' }]}
      />
      <Card>
        <Card.Body>
          {error && (
            <p className="text-sm text-red-600 mb-3">
              {error.message} <button type="button" className="underline" onClick={() => refetch()}>Retry</button>
            </p>
          )}
          <p className="text-sm font-medium mb-2">Current heat-wise stock</p>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2">Supplier</th>
                  <th>Type</th>
                  <th>Heat</th>
                  <th>On hand</th>
                  <th>Available</th>
                  <th>Ring wt</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${row.vendor_id}-${row.product_id}-${row.heat_number}`} className="border-b border-gray-50">
                    <td className="py-2">{row.vendor_name}</td>
                    <td>{row.product_sku}</td>
                    <td>{row.heat_number}</td>
                    <td>{row.quantity_on_hand}</td>
                    <td>{row.quantity_available}</td>
                    <td>{row.per_ring_weight}</td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr><td colSpan={6} className="py-6 text-center text-gray-400">No heat-wise stock yet</td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card.Body>
      </Card>
      <Card>
        <Card.Body className="space-y-3">
          <div className="flex items-end gap-4">
            <div className="w-48">
              <Input label="Day-wise closing date" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2">Supplier</th>
                <th>Type</th>
                <th>Heat</th>
                <th>Opening</th>
                <th>Inward</th>
                <th>Outward</th>
                <th>Closing</th>
              </tr>
            </thead>
            <tbody>
              {closeRows.map((row) => (
                <tr key={`${row.vendor_id}-${row.product_id}-${row.heat_number}`} className="border-b border-gray-50">
                  <td className="py-2">{row.vendor_name}</td>
                  <td>{row.product_sku}</td>
                  <td>{row.heat_number}</td>
                  <td>{row.opening_qty}</td>
                  <td>{row.inward_qty}</td>
                  <td>{row.outward_qty}</td>
                  <td>{row.closing_qty}</td>
                </tr>
              ))}
              {closeRows.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-gray-400">No movements on this date</td></tr>
              )}
            </tbody>
          </table>
        </Card.Body>
      </Card>
    </div>
  );
};

export default RingsStockPage;
