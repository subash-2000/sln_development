import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBranch, useUpdateBranch } from '../hooks/use-branches';
import BranchForm from '../components/BranchForm';
import Loader from '../../../components/common/Loader';

const BranchEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState(null);
  const { data: branch, isLoading: isFetching } = useBranch(id);
  const { mutateAsync: updateBranch, isPending: isUpdating } = useUpdateBranch();

  const handleSubmit = async (data) => {
    try {
      setErrorMessage(null);
      await updateBranch({
        id,
        data: {
          ...data,
          status: data.is_active ? 'ACTIVE' : 'INACTIVE',
          gstin: data.tax_id || data.gstin || undefined,
        },
      });
      navigate('/branches');
    } catch (err) {
      console.error('Failed to update branch:', err);
      const detail =
        err.response?.data?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to update branch';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Edit Branch</h1>

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

      <BranchForm initialData={branch} onSubmit={handleSubmit} isLoading={isUpdating} isEdit />
    </div>
  );
};

export default BranchEditPage;

