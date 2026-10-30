import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import PageHeader from '../../../../components/common/PageHeader';
import CategoryForm from '../components/CategoryForm';
import { useCreateCategory } from '../hooks/use-categories';

const CategoryCreatePage = () => {
  const navigate = useNavigate();
  const { mutateAsync: createCategory, isPending } = useCreateCategory();
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSubmit = async (formData) => {
    setErrorMsg(null);
    try {
      await createCategory(formData);
      navigate('/products/categories');
    } catch (error) {
      console.error('Failed to create category:', error);
      setErrorMsg(
        error?.response?.data?.detail ||
        error?.message ||
        'Failed to create product category. Please verify the code and details.'
      );
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Add Product Category"
        description="Define product classifications, taxonomy, and category hierarchy."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products', to: '/products' },
          { label: 'Product Categories', to: '/products/categories' },
          { label: 'Add Category' },
        ]}
      />

      {errorMsg && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm w-full">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
          <span>{errorMsg}</span>
        </div>
      )}

      <CategoryForm onSubmit={handleSubmit} isLoading={isPending} isEdit={false} />
    </div>
  );
};

export default CategoryCreatePage;
