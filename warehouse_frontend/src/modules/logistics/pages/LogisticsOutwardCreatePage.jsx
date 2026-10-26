import React from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import LogisticsOutwardForm from '../components/LogisticsOutwardForm';
import { useCreateDispatchOrder } from '../hooks/use-logistics';

const LogisticsOutwardCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createDispatch, isPending } = useCreateDispatchOrder();

  const handleSubmit = async (data) => {
    await createDispatch(data);
    navigate('/logistics/outward');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Outward Dispatch"
        description="Create a delivery challan / dispatch order for outbound logistics."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Operations' },
          { label: 'Outward', to: '/logistics/outward' },
          { label: 'Create' },
        ]}
      />
      <LogisticsOutwardForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default LogisticsOutwardCreatePage;
