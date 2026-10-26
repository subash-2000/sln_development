import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useUser, useUpdateUser } from '../hooks/use-users';
import UserForm from '../components/UserForm';
import Loader from '../../../components/common/Loader';

const UserEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState(null);
  const { data: user, isLoading: isFetching } = useUser(id);
  const { mutateAsync: updateUser, isPending: isUpdating } = useUpdateUser();

  const handleSubmit = async (data) => {
    try {
      setErrorMessage(null);
      await updateUser({ id, data });
      navigate('/users');
    } catch (error) {
      console.error('Failed to update user:', error);
      const detail =
        error.response?.data?.message ||
        error.response?.data?.detail ||
        error.message ||
        'Failed to update user';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  };

  if (isFetching) return <Loader fullPage />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Edit User</h1>
        <p className="text-gray-500 text-sm mt-1">Update user information and access controls.</p>
      </div>

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

      <UserForm 
        initialData={user} 
        onSubmit={handleSubmit} 
        isLoading={isUpdating} 
        isEdit 
      />
    </div>
  );
};

export default UserEditPage;
