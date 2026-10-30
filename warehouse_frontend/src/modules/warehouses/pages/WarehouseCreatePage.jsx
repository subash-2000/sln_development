import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth.store';
import { useCreateWarehouse } from '../hooks/use-warehouses';
import WarehouseForm from '../components/WarehouseForm';
import PageHeader from '../../../components/common/PageHeader';

const WarehouseCreatePage = () => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { mutateAsync: createWarehouse, isPending } = useCreateWarehouse();
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (data) => {
    setErrorMessage(null);
    try {
      const payload = {
        company_id: data.company_id || companyContext,
        branch_id: data.branch_id ? data.branch_id : null,
        code: data.code?.trim().toUpperCase(),
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

      await createWarehouse(payload);
      navigate('/warehouses');
    } catch (error) {
      console.error('Failed to create warehouse:', error);
      const msg = error?.message || error?.details?.message || 'Failed to create warehouse. Please verify all details.';
      setErrorMessage(msg);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add New Warehouse"
        description="Register a new storage facility under a company and optional operating branch."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Warehouses', to: '/warehouses' },
          { label: 'Add Warehouse' },
        ]}
      />
      <WarehouseForm 
        onSubmit={handleSubmit} 
        isLoading={isPending} 
        serverError={errorMessage} 
      />
    </div>
  );
};

export default WarehouseCreatePage;
