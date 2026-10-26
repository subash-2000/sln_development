import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateCustomer } from '../hooks/use-customers';
import CustomerForm from '../components/CustomerForm';
import PageHeader from '../../../components/common/PageHeader';

const BuyerCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createCustomer, isPending } = useCreateCustomer();

  const handleSubmit = async (data) => {
    try {
      await createCustomer({
        ...data,
        company_id: companyContext,
        billing_address: data.address || undefined,
        is_buyer: true,
        status: data.is_active === false ? 'INACTIVE' : 'ACTIVE',
      });
      navigate('/buyers');
    } catch (error) {
      console.error('Failed to create buyer:', error);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add Buyer"
        description="Create a buyer used on pick, dispatch and sales."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Buyers', to: '/buyers' },
          { label: 'Add Buyer' },
        ]}
      />
      <CustomerForm onSubmit={handleSubmit} isLoading={isPending} mode="buyer" />
    </div>
  );
};

export default BuyerCreatePage;
