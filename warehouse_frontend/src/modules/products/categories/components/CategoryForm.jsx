import React, { useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { getCategorySchema } from '../schemas/category.schema';
import { useCategories } from '../hooks/use-categories';
import { useCompanies } from '../../../companies/hooks/use-companies';
import { useAuthStore } from '../../../../store/auth.store';
import Button from '../../../../components/ui/Button';
import Input from '../../../../components/ui/Input';
import Card from '../../../../components/ui/Card';
import { useNavigate } from 'react-router-dom';

const CategoryForm = ({ initialData, onSubmit, isLoading = false, isEdit = false }) => {
  const navigate = useNavigate();
  const { companyContext } = useAuthStore();
  const { data: companiesData } = useCompanies({ pageSize: 100 });
  const companies = useMemo(() => {
    return (companiesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [companiesData]);

  const { data: categoriesData } = useCategories({ page_size: 200 });
  const existingCategories = useMemo(() => {
    const list = categoriesData?.items || (Array.isArray(categoriesData) ? categoriesData : []);
    return list.slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [categoriesData]);

  const currentCategoryId = initialData?.id || null;

  // Filter out the category itself from parent options when editing
  const parentOptions = useMemo(() => {
    return existingCategories.filter((cat) => !currentCategoryId || String(cat.id) !== String(currentCategoryId));
  }, [existingCategories, currentCategoryId]);

  const defaultValues = useMemo(() => {
    if (!initialData) {
      return {
        company_id: companyContext || (companies[0]?.id ?? ''),
        code: '',
        name: '',
        parent_id: '',
        description: '',
        is_active: true,
      };
    }
    return {
      company_id: initialData.company_id || companyContext || '',
      code: initialData.code || '',
      name: initialData.name || '',
      parent_id: initialData.parent_id || '',
      description: initialData.description || '',
      is_active: initialData.is_active !== undefined ? Boolean(initialData.is_active) : (initialData.status === 'ACTIVE' || !initialData.status),
    };
  }, [initialData, companyContext, companies]);

  const schema = useMemo(
    () => getCategorySchema(isEdit, existingCategories, currentCategoryId),
    [isEdit, existingCategories, currentCategoryId]
  );

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues,
    values: defaultValues,
  });

  const isActive = watch('is_active');

  const handleFormSubmit = (formData) => {
    onSubmit({
      ...formData,
      code: formData.code?.trim().toUpperCase(),
      name: formData.name?.trim(),
      description: formData.description?.trim() || null,
      parent_id: formData.parent_id || null,
      company_id: formData.company_id || null,
      status: formData.is_active ? 'ACTIVE' : 'INACTIVE',
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="w-full space-y-6">
      <Card>
        <Card.Header>
          <h3 className="text-base font-semibold text-gray-900">
            {isEdit ? 'Edit Category Details' : 'Category Information'}
          </h3>
          <p className="text-xs text-gray-500">
            Configure hierarchy, classification codes, and display properties.
          </p>
        </Card.Header>
        <Card.Body className="space-y-5">
          {companies.length > 1 && !isEdit && (
            <div className="space-y-1.5">
              <label htmlFor="company_id" className="text-sm font-medium text-gray-700">
                Company Scope
              </label>
              <select
                id="company_id"
                {...register('company_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition"
              >
                <option value="">Global / Active Context</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
              {errors.company_id && (
                <p className="text-xs text-red-500 font-medium">{errors.company_id.message}</p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Category Code"
              placeholder="e.g. ELEC, GRAINS"
              isRequired
              error={errors.code?.message}
              disabled={isEdit}
              helperText={isEdit ? 'Category code cannot be changed once created.' : 'Unique identifier, uppercase.'}
              {...register('code', {
                onChange: (e) => {
                  setValue('code', e.target.value.toUpperCase());
                },
              })}
            />

            <Input
              label="Category Name"
              placeholder="e.g. Electronics & Hardware"
              isRequired
              error={errors.name?.message}
              {...register('name')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="parent_id" className="text-sm font-medium text-gray-700">
                Parent Category (Optional)
              </label>
              <select
                id="parent_id"
                {...register('parent_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition"
              >
                <option value="">None (Top-level Category)</option>
                {parentOptions.map((parent) => (
                  <option key={parent.id} value={parent.id}>
                    {parent.name} ({parent.code})
                  </option>
                ))}
              </select>
              {errors.parent_id && (
                <p className="text-xs text-red-500 font-medium">{errors.parent_id.message}</p>
              )}
              <p className="text-xs text-gray-500">
                Nest under another category to establish a multi-level hierarchy.
              </p>
            </div>

            <div className="space-y-1.5 flex flex-col justify-center">
              <label className="text-sm font-medium text-gray-700 mb-1">Status</label>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setValue('is_active', !isActive)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    isActive ? 'bg-primary-600' : 'bg-gray-200'
                  }`}
                  role="switch"
                  aria-checked={isActive}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      isActive ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
                <span className={`text-sm font-medium ${isActive ? 'text-green-600' : 'text-gray-500'}`}>
                  {isActive ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="description" className="text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              id="description"
              rows={3}
              placeholder="Enter category description or handling notes..."
              {...register('description')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition placeholder:text-gray-400"
            />
            {errors.description && (
              <p className="text-xs text-red-500 font-medium">{errors.description.message}</p>
            )}
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end gap-3 bg-gray-50/50">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/products/categories')}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Save Changes' : 'Create Category'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default CategoryForm;
