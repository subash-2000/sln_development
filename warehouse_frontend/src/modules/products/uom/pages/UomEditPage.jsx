import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import PageHeader from '../../../../components/common/PageHeader';
import Loader from '../../../../components/common/Loader';
import UomForm from '../components/UomForm';
import { useUom, useUpdateUom } from '../hooks/use-uom-master';

const UomEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: uom, isLoading, error } = useUom(id);
  const { mutateAsync: updateUom, isPending } = useUpdateUom();

  const handleSubmit = async (data) => {
    try {
      await updateUom({ id, data });
      navigate('/products/uom');
    } catch (e) {
      window.alert(e?.message || 'Failed to update UOM');
    }
  };

  if (isLoading) return <Loader className="py-16" />;
  if (error || !uom) {
    return (
      <p className="p-6 text-gray-600">
        UOM not found.{' '}
        <button type="button" className="text-primary-600 underline" onClick={() => navigate('/products/uom')}>
          Back to list
        </button>
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Edit ${uom.code}`}
        description={uom.name}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'UOM', to: '/products/uom' },
          { label: uom.code },
        ]}
      />
      <UomForm
        isEdit
        isLoading={isPending}
        onSubmit={handleSubmit}
        defaultValues={{
          category_id: uom.category_id,
          code: uom.code,
          name: uom.name,
          uom_type: uom.uom_type,
          factor: Number(uom.factor),
          rounding_precision: Number(uom.rounding_precision),
          status: uom.status || 'ACTIVE',
        }}
      />
    </div>
  );
};

export default UomEditPage;
