import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateCustomer } from '../hooks/use-customers';
import CustomerForm from '../components/CustomerForm';
import PageHeader from '../../../components/common/PageHeader';

const CustomerCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createCustomer, isPending } = useCreateCustomer();

  const handleSubmit = async (data) => {
    try {
      await createCustomer({
        ...data,
        company_id: companyContext,
      });
      navigate('/customers');
    } catch (error) {
      console.error('Failed to create customer:', error);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add New Customer"
        description="Register a new customer profile and commercial terms."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Customers', to: '/customers' },
          { label: 'Add Customer' },
        ]}
      />
      <CustomerForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default CustomerCreatePage;
