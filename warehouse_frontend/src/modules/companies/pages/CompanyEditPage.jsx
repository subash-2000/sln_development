import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCompany, useUpdateCompany } from '../hooks/use-companies';
import CompanyForm from '../components/CompanyForm';
import Loader from '../../../components/common/Loader';

const CompanyEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: company, isLoading: isFetching } = useCompany(id);
  const { mutateAsync: updateCompany, isPending: isUpdating } = useUpdateCompany();

  const handleSubmit = async (data, formHelpers = {}) => {
    try {
      await updateCompany({
        id,
        data: {
          ...data,
          status: data.is_active ? 'ACTIVE' : 'INACTIVE',
          gstin: data.tax_id || data.gstin || undefined,
        },
      });
      navigate('/companies');
    } catch (err) {
      console.error('Failed to update company:', err);
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
      <h1 className="text-2xl font-bold text-gray-900">Edit Company</h1>
      <CompanyForm initialData={company} onSubmit={handleSubmit} isLoading={isUpdating} isEdit />
    </div>
  );
};

export default CompanyEditPage;
