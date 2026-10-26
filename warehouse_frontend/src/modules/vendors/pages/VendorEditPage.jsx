import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useVendor, useUpdateVendor } from '../hooks/use-vendors';
import VendorForm from '../components/VendorForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const VendorEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: vendor, isLoading: isFetching } = useVendor(id);
  const { mutateAsync: updateVendor, isPending: isUpdating } = useUpdateVendor();

  const handleSubmit = async (data, formHelpers = {}) => {
    try {
      await updateVendor({
        id,
        data: {
          ...data,
          status: data.is_active ? 'ACTIVE' : 'INACTIVE',
          billing_address: data.address,
        },
      });
      navigate('/suppliers');
    } catch (err) {
      console.error('Failed to update vendor:', err);
      const field = err.response?.data?.details?.field;
      const message = err.response?.data?.message || err.message;
      if (field && formHelpers.setError) {
        formHelpers.setError(field, { type: 'server', message });
      }
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Supplier"
        description="Update supplier contact details and operational status."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Suppliers', to: '/suppliers' },
          { label: 'Edit Supplier' },
        ]}
      />
      <VendorForm 
        initialData={vendor} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default VendorEditPage;
