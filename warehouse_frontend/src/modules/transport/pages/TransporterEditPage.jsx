import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';
import Card from '../../../components/ui/Card';
import Button from '../../../components/ui/Button';
import TransporterForm from '../components/TransporterForm';
import { useTransporter, useUpdateTransporter } from '../hooks/use-transporters';

const TransporterEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: transporter, isLoading, error, refetch } = useTransporter(id);
  const { mutateAsync: updateTransporter, isPending } = useUpdateTransporter();

  if (isLoading) return <Loader fullPage />;
  if (error || !transporter) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-600">Transporter not found.</p>
        <Button className="mt-4" onClick={() => navigate('/transport')}>Back to list</Button>
      </Card>
    );
  }

  const handleUpdate = async (data) => {
    await updateTransporter({ id: transporter.id, data });
    refetch();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={transporter.name}
        description={transporter.code}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Transport', to: '/transport' },
          { label: transporter.code },
        ]}
      />
      <TransporterForm
        initialData={transporter}
        onSubmit={handleUpdate}
        isLoading={isPending}
        isEdit
      />
    </div>
  );
};

export default TransporterEditPage;
