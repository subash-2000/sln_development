import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateUser } from '../hooks/use-users';
import UserForm from '../components/UserForm';

const UserCreatePage = () => {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState(null);
  const { mutateAsync: createUser, isPending } = useCreateUser();

  const handleSubmit = async (data) => {
    try {
      setErrorMessage(null);
      await createUser(data);
      navigate('/users');
    } catch (error) {
      console.error('Failed to create user:', error);
      const detail =
        error.response?.data?.message ||
        error.response?.data?.detail ||
        error.message ||
        'Failed to create user';
      setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Add New User</h1>
        <p className="text-gray-500 text-sm mt-1">Create a new system user and assign roles.</p>
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

      <UserForm onSubmit={handleSubmit} isLoading={isPending} />
    </div>
  );
};

export default UserCreatePage;
