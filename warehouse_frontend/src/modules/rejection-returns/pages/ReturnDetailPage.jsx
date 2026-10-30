import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import StatusBadge from '../../../components/ui/StatusBadge';
import Loader from '../../../components/common/Loader';
import { formatDateTime } from '../../../utils/formatters';
import { useReturn, useReturnActions } from '../hooks/use-returns';

const ReturnDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: order, isLoading, error, refetch } = useReturn(id);
  const { receive, inspect, complete, cancel } = useReturnActions();

  const runAction = async (mutation, label) => {
    try {
      await mutation.mutateAsync(id);
      refetch();
    } catch (e) {
      console.error(e);
      window.alert(e?.message || `${label} failed`);
    }
  };

  const handleInspectAndComplete = async () => {
    if (!order?.lines?.length) return;
    try {
      await inspect.mutateAsync({
        id,
        data: {
          inspection_notes: 'Accepted per warehouse review',
          items: order.lines.map((line) => ({
            line_id: line.id,
            quantity_accepted: Number(line.quantity_returned),
            quantity_rejected: 0,
            disposition: 'RESTOCK',
          })),
        },
      });
      await complete.mutateAsync(id);
      refetch();
    } catch (e) {
      console.error(e);
      window.alert(e?.message || 'Inspect / complete failed');
    }
  };

  if (isLoading) {
    return <Loader className="py-16" />;
  }

  if (error || !order) {
    return (
      <div className="p-6 text-center text-gray-600">
        Could not load return order.
        <Button className="mt-4" variant="secondary" onClick={() => navigate('/rejection-returns')}>
          Back to list
        </Button>
      </div>
    );
  }

  const isDraft = order.status === 'DRAFT';
  const isReceived = order.status === 'RECEIVED';
  const isInspected = order.status === 'INSPECTED';
  const canCancel = !['COMPLETED', 'CANCELLED'].includes(order.status);

  return (
    <div className="space-y-6">
      <PageHeader
        title={order.return_number}
        description={order.reason || 'Return & rejection order'}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Rejection & Returns', to: '/rejection-returns' },
          { label: order.return_number },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            {isDraft && (
              <Button
                onClick={() => runAction(receive, 'Receive')}
                disabled={receive.isPending}
              >
                Mark received
              </Button>
            )}
            {isReceived && (
              <Button onClick={handleInspectAndComplete} disabled={inspect.isPending || complete.isPending}>
                Inspect & complete
              </Button>
            )}
            {isInspected && (
              <Button onClick={() => runAction(complete, 'Complete')} disabled={complete.isPending}>
                Complete (post stock)
              </Button>
            )}
            {canCancel && (
              <Button
                variant="secondary"
                onClick={() => runAction(cancel, 'Cancel')}
                disabled={cancel.isPending}
              >
                Cancel
              </Button>
            )}
          </div>
        }
      />

      <Card>
        <Card.Body className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Status</span>
            <div className="mt-1"><StatusBadge status={order.status} /></div>
          </div>
          <div>
            <span className="text-gray-500">Type</span>
            <p className="font-medium mt-1">{order.return_type?.replace(/_/g, ' ')}</p>
          </div>
          <div>
            <span className="text-gray-500">Return date</span>
            <p className="font-medium mt-1">{order.return_date}</p>
          </div>
          <div>
            <span className="text-gray-500">Warehouse</span>
            <p className="font-medium mt-1">{order.warehouse_name || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Supplier</span>
            <p className="font-medium mt-1">{order.vendor_name || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Customer</span>
            <p className="font-medium mt-1">{order.customer_name || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Created At</span>
            <p className="font-medium mt-1">{order.created_at ? formatDateTime(order.created_at) : '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Created By</span>
            <p className="font-medium mt-1">{order.created_by || '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Last Updated</span>
            <p className="font-medium mt-1">{order.updated_at ? formatDateTime(order.updated_at) : '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Updated By</span>
            <p className="font-medium mt-1">{order.updated_by || '—'}</p>
          </div>
          {order.notes && (
            <div className="md:col-span-3">
              <span className="text-gray-500">Notes</span>
              <p className="mt-1 whitespace-pre-wrap">{order.notes}</p>
            </div>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <h3 className="text-lg font-medium">Lines</h3>
        </Card.Header>
        <Card.Body className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2 pr-4">SKU</th>
                <th className="py-2 pr-4">Product</th>
                <th className="py-2 pr-4">Qty returned</th>
                <th className="py-2 pr-4">Accepted</th>
                <th className="py-2 pr-4">Rejected</th>
                <th className="py-2 pr-4">Lot</th>
                <th className="py-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {(order.lines || []).map((line) => (
                <tr key={line.id} className="border-b border-gray-50">
                  <td className="py-2 pr-4 font-mono">{line.product_sku}</td>
                  <td className="py-2 pr-4">{line.product_name}</td>
                  <td className="py-2 pr-4">{line.quantity_returned}</td>
                  <td className="py-2 pr-4">{line.quantity_accepted}</td>
                  <td className="py-2 pr-4">{line.quantity_rejected}</td>
                  <td className="py-2 pr-4">{line.lot_number || '—'}</td>
                  <td className="py-2">{line.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card.Body>
      </Card>

      {isDraft && (
        <p className="text-sm text-gray-500">
          Excel-imported orders start as <strong>DRAFT</strong>. Use <strong>Mark received</strong>, then{' '}
          <strong>Inspect & complete</strong> to post stock movements when you are ready.
        </p>
      )}
    </div>
  );
};

export default ReturnDetailPage;
