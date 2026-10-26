import React from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../../../../components/common/PageHeader';
import UomForm from '../components/UomForm';
import { useCreateUom } from '../hooks/use-uom-master';

const UomCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createUom, isPending } = useCreateUom();

  const handleSubmit = async (data) => {
    try {
      const created = await createUom(data);
      navigate(created?.id ? `/products/uom/${created.id}/edit` : '/products/uom');
    } catch (e) {
      window.alert(e?.message || 'Failed to create UOM');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New unit of measure"
        description="Add a unit for products and inventory (e.g. Nos, Kg, Box)."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'UOM', to: '/products/uom' },
          { label: 'New' },
        ]}
      />
      <UomForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default UomCreatePage;
