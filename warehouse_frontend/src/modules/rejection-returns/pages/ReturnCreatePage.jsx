import React from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../../components/common/PageHeader';
import ReturnForm from '../components/ReturnForm';
import { useCreateReturn } from '../hooks/use-returns';

const ReturnCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createReturn, isPending } = useCreateReturn();

  const handleSubmit = async (data) => {
    try {
      const order = await createReturn(data);
      if (order?.id) {
        navigate(`/returns/list/${order.id}`);
      } else {
        navigate('/rejection-returns');
      }
    } catch (error) {
      console.error('Failed to create return:', error);
      window.alert(error?.message || 'Could not create return order. Check required fields and permissions.');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Return & Rejection"
        description="Create a customer RMA or supplier rejection / return-to-vendor (RTV) order."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Returns' },
          { label: 'Rejection & Returns', to: '/rejection-returns' },
          { label: 'New Return' },
        ]}
      />
      <ReturnForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default ReturnCreatePage;
