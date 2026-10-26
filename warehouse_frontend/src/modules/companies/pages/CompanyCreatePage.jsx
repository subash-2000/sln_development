import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateCompany } from '../hooks/use-companies';
import CompanyForm from '../components/CompanyForm';

const CompanyCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createCompany, isPending } = useCreateCompany();

  const handleSubmit = async (data, formHelpers = {}) => {
    try {
      await createCompany({
        ...data,
        status: data.is_active ? 'ACTIVE' : 'INACTIVE',
        gstin: data.tax_id || data.gstin || undefined,
      });
      navigate('/companies');
    } catch (err) {
      console.error('Failed to create company:', err);
      const field = err.response?.data?.details?.field;
      const message = err.response?.data?.message || err.message;
      if (field && formHelpers.setError) {
        formHelpers.setError(field, { type: 'server', message });
      }
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Create New Company</h1>
      <CompanyForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default CompanyCreatePage;
