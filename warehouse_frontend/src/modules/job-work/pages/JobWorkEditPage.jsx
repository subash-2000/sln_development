import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import Loader from '../../../components/common/Loader';
import StatusBadge from '../../../components/ui/StatusBadge';
import { useIssueJobWorkMaterials, useJobWorkOrder } from '../hooks/use-job-work';

const JobWorkEditPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const { data: order, isLoading, error, refetch } = useJobWorkOrder(id);
  const { mutateAsync: issueMaterials, isPending: isIssuing } = useIssueJobWorkMaterials();

  const handleIssue = async () => {
    if (!order?.lines?.length) return;
    const items = order.lines.map((line) => ({
      product_id: line.product_id,
      quantity: Number(line.ordered_qty) - Number(line.issued_qty || 0) || Number(line.ordered_qty),
    })).filter((item) => item.quantity > 0);
    if (!items.length) {
      window.alert('All materials are already issued for this order.');
      return;
    }
    await issueMaterials({ id: order.id, data: { items } });
    refetch();
  };

  if (isLoading) return <Loader fullPage />;
  if (error || !order) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-600">Unable to load job work order.</p>
        <Button className="mt-4" onClick={() => navigate('/job-work/register')}>Back to register</Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={order.job_work_number}
        description={`${order.vendor_name || 'Supplier'} · ${order.warehouse_name || 'Warehouse'}`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Job Work Register', to: '/job-work/register' },
          { label: order.job_work_number },
        ]}
        actions={
          order.status === 'DRAFT' ? (
            <Button onClick={handleIssue} isLoading={isIssuing}>Issue materials</Button>
          ) : null
        }
      />

      <Card>
        <Card.Body className="space-y-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <span><strong>Status:</strong> <StatusBadge status={order.status} /></span>
            <span><strong>Type:</strong> {order.order_type}</span>
            <span><strong>Issue date:</strong> {order.issue_date}</span>
          </div>
          <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-2">Product</th>
                <th className="text-right px-4 py-2">Ordered</th>
                <th className="text-right px-4 py-2">Issued</th>
                <th className="text-right px-4 py-2">Returned</th>
              </tr>
            </thead>
            <tbody>
              {order.lines?.map((line) => (
                <tr key={line.id} className="border-t border-gray-100">
                  <td className="px-4 py-2">{line.product_name || line.product_id}</td>
                  <td className="px-4 py-2 text-right">{line.ordered_qty}</td>
                  <td className="px-4 py-2 text-right">{line.issued_qty}</td>
                  <td className="px-4 py-2 text-right">{line.returned_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {order.notes && <p className="text-sm text-gray-600"><strong>Notes:</strong> {order.notes}</p>}
        </Card.Body>
      </Card>
    </div>
  );
};

export default JobWorkEditPage;
