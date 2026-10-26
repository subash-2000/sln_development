import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCustomer, useUpdateCustomer } from '../hooks/use-customers';
import CustomerForm from '../components/CustomerForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const BuyerEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: buyer, isLoading: isFetching } = useCustomer(id);
  const { mutateAsync: updateCustomer, isPending: isUpdating } = useUpdateCustomer();

  const initialData = useMemo(() => {
    if (!buyer) return null;
    return {
      ...buyer,
      address: buyer.billing_address || '',
      is_active: buyer.status === 'ACTIVE',
    };
  }, [buyer]);

  const handleSubmit = async (data) => {
    try {
      await updateCustomer({
        id,
        data: {
          name: data.name,
          gstin: data.gstin || null,
          contact_person: data.contact_person || null,
          phone: data.phone || null,
          email: data.email || null,
          billing_address: data.address || null,
          is_buyer: true,
          status: data.is_active === false ? 'INACTIVE' : 'ACTIVE',
        },
      });
      navigate('/buyers');
    } catch (error) {
      console.error('Failed to update buyer:', error);
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Buyer"
        description="Update buyer master details."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Buyers', to: '/buyers' },
          { label: 'Edit Buyer' },
        ]}
      />
      <CustomerForm
        initialData={initialData}
        onSubmit={handleSubmit}
        isLoading={isUpdating}
        isEdit
        mode="buyer"
      />
    </div>
  );
};

export default BuyerEditPage;
