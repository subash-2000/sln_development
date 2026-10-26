import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCustomer, useUpdateCustomer } from '../hooks/use-customers';
import CustomerForm from '../components/CustomerForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const CustomerEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: customer, isLoading: isFetching } = useCustomer(id);
  const { mutateAsync: updateCustomer, isPending: isUpdating } = useUpdateCustomer();

  const handleSubmit = async (data) => {
    try {
      await updateCustomer({ id, data });
      navigate('/customers');
    } catch (error) {
      console.error('Failed to update customer:', error);
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Customer"
        description="Update customer contact details and billing profile."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Customers', to: '/customers' },
          { label: 'Edit Customer' },
        ]}
      />
      <CustomerForm 
        initialData={customer} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default CustomerEditPage;
