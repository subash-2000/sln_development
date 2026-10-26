import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useWarehouse, useUpdateWarehouse } from '../hooks/use-warehouses';
import WarehouseForm from '../components/WarehouseForm';
import PageHeader from '../../../components/common/PageHeader';
import Loader from '../../../components/common/Loader';

const WarehouseEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: warehouse, isLoading: isFetching } = useWarehouse(id);
  const { mutateAsync: updateWarehouse, isPending: isUpdating } = useUpdateWarehouse();

  const handleSubmit = async (data) => {
    try {
      await updateWarehouse({ id, data });
      navigate('/warehouses');
    } catch (error) {
      console.error('Failed to update warehouse:', error);
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit Warehouse"
        description="Update facility details and operational status."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Warehouses', to: '/warehouses' },
          { label: 'Edit Warehouse' },
        ]}
      />
      <WarehouseForm 
        initialData={warehouse} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default WarehouseEditPage;
