import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import PageHeader from '../../../../components/common/PageHeader';
import Button from '../../../../components/ui/Button';
import CategoryForm from '../components/CategoryForm';
import { useCategory, useUpdateCategory } from '../hooks/use-categories';

const CategoryEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: category, isLoading, error } = useCategory(id);
  const { mutateAsync: updateCategory, isPending } = useUpdateCategory();
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSubmit = async (formData) => {
    setErrorMsg(null);
    try {
      await updateCategory({
        id,
        data: {
          name: formData.name,
          parent_id: formData.parent_id || null,
          description: formData.description || null,
          status: formData.status,
        },
      });
      navigate('/masters/products/categories');
    } catch (err) {
      console.error('Failed to update category:', err);
      setErrorMsg(
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to update product category. Please try again.'
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !category) {
    return (
      <div className="space-y-4 w-full">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          Failed to load category details. It may not exist or has been removed.
        </div>
        <Button variant="outline" onClick={() => navigate('/masters/products/categories')}>
          <ArrowLeft size={16} className="mr-2" />
          Back to Categories
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Edit Category: ${category.name}`}
        description={`Code: ${category.code} | Modify classification, parent hierarchy, and status.`}
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products', to: '/masters/products' },
          { label: 'Product Categories', to: '/masters/products/categories' },
          { label: 'Edit Category' },
        ]}
      />

      {errorMsg && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm w-full">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
          <span>{errorMsg}</span>
        </div>
      )}

      <CategoryForm
        initialData={category}
        onSubmit={handleSubmit}
        isLoading={isPending}
        isEdit={true}
      />
    </div>
  );
};

export default CategoryEditPage;
