import React, { useState } from 'react';
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
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (data) => {
    setErrorMessage(null);
    try {
      const payload = {
        branch_id: data.branch_id ? data.branch_id : null,
        name: data.name?.trim(),
        warehouse_type: data.warehouse_type,
        city: data.city?.trim() || null,
        state: data.state?.trim() || null,
        contact_person: data.contact_person?.trim() || null,
        phone: data.phone?.trim() || null,
        address: data.address?.trim() || null,
        address_line1: data.address?.trim() || null,
        status: data.is_active ? 'ACTIVE' : 'INACTIVE',
      };

      await updateWarehouse({ id, data: payload });
      navigate('/warehouses');
    } catch (error) {
      console.error('Failed to update warehouse:', error);
      const msg = error?.message || error?.details?.message || 'Failed to update warehouse. Please verify all details.';
      setErrorMessage(msg);
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
        serverError={errorMessage}
      />
    </div>
  );
};

export default WarehouseEditPage;
