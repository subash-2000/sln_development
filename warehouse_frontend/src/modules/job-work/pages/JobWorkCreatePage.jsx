import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateJobWorkOrder } from '../hooks/use-job-work';
import JobWorkForm from '../components/JobWorkForm';
import PageHeader from '../../../components/common/PageHeader';

const JobWorkCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createOrder, isPending } = useCreateJobWorkOrder();

  const handleSubmit = async (data) => {
    await createOrder(data);
    navigate('/job-work/register');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create Job Work"
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Operations' },
          { label: 'Job Work Register', to: '/job-work/register' },
          { label: 'New Order' },
        ]}
      />
      <JobWorkForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default JobWorkCreatePage;
