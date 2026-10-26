import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateWarehouse } from '../hooks/use-warehouses';
import WarehouseForm from '../components/WarehouseForm';
import PageHeader from '../../../components/common/PageHeader';

const WarehouseCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createWarehouse, isPending } = useCreateWarehouse();

  const handleSubmit = async (data) => {
    try {
      await createWarehouse({
        ...data,
        company_id: data.company_id || companyContext,
      });
      navigate('/warehouses');
    } catch (error) {
      console.error('Failed to create warehouse:', error);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add New Warehouse"
        description="Register a new storage facility under a company and branch."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Warehouses', to: '/warehouses' },
          { label: 'Add Warehouse' },
        ]}
      />
      <WarehouseForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default WarehouseCreatePage;
