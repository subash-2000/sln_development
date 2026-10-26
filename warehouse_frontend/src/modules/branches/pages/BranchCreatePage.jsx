import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateBranch } from '../hooks/use-branches';
import BranchForm from '../components/BranchForm';

const BranchCreatePage = () => {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState(null);
  const { mutateAsync: createBranch, isPending } = useCreateBranch();

  const handleSubmit = async (data) => {
    try {
      setErrorMessage(null);
      await createBranch({
        ...data,
        status: data.is_active ? 'ACTIVE' : 'INACTIVE',
        gstin: data.tax_id || data.gstin || undefined,
      });
      navigate('/branches');
    } catch (err) {
      console.error('Failed to create branch:', err);
      const detail =
        err.response?.data?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to create branch';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Create New Branch</h1>

      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-red-500 hover:text-red-700 font-bold ml-4"
          >
            ×
          </button>
        </div>
      )}

      <BranchForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default BranchCreatePage;
