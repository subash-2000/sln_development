import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateVendor } from '../hooks/use-vendors';
import VendorForm from '../components/VendorForm';
import PageHeader from '../../../components/common/PageHeader';

const VendorCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createVendor, isPending } = useCreateVendor();

  const handleSubmit = async (data, formHelpers = {}) => {
    try {
      await createVendor({
        ...data,
        company_id: companyContext,
        status: data.is_active ? 'ACTIVE' : 'INACTIVE',
        billing_address: data.address,
      });
      navigate('/suppliers');
    } catch (err) {
      console.error('Failed to create vendor:', err);
      const field = err.response?.data?.details?.field;
      const message = err.response?.data?.message || err.message;
      if (field && formHelpers.setError) {
        formHelpers.setError(field, { type: 'server', message });
      }
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add New Supplier"
        description="Register a new supplier or service provider in the system."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Suppliers', to: '/suppliers' },
          { label: 'Add Supplier' },
        ]}
      />
      <VendorForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default VendorCreatePage;
