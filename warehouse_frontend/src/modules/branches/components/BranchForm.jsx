import React, { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { getBranchSchema, branchSchema } from '../schemas/branch.schema';
import { useCompanies } from '../../companies/hooks/use-companies';
import { useBranches } from '../hooks/use-branches';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const getInitialBranchValues = (data) => {
  if (!data) {
    return {
      company_id: '',
      code: '',
      name: '',
      tax_id: '',
      address: '',
      phone: '',
      email: '',
      is_active: true,
    };
  }
  return {
    company_id: data.company_id || '',
    code: data.code || '',
    name: data.name || '',
    tax_id: data.tax_id || data.gstin || '',
    address: data.address || '',
    phone: data.phone || '',
    email: data.email || '',
    is_active: data.is_active !== undefined ? Boolean(data.is_active) : (data.status === 'ACTIVE' || !data.status),
  };
};

const BranchForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: companiesData } = useCompanies({ page_size: 100 });
  const companies = useMemo(() => {
    return (companiesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [companiesData]);

  const { data: branchesData } = useBranches({ page_size: 1000 });
  const existingBranches = useMemo(() => {
    return branchesData?.items || (Array.isArray(branchesData) ? branchesData : []);
  }, [branchesData]);

  const currentBranchId = initialData?.id || null;

  const schema = useMemo(
    () => getBranchSchema(isEdit, existingBranches, currentBranchId),
    [isEdit, existingBranches, currentBranchId]
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: getInitialBranchValues(initialData),
  });

  useEffect(() => {
    if (initialData) {
      reset(getInitialBranchValues(initialData));
    }
  }, [initialData, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Company</label>
              <select
                {...register('company_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="">Select Company</option>
                {companies.map(company => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
              {errors.company_id && <p className="text-xs text-red-500">{errors.company_id.message}</p>}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Branch Code"
                placeholder="BR-01"
                error={errors.code?.message}
                isRequired
                {...register('code')}
              />
              <Input
                label="Branch Name"
                placeholder="Mumbai Branch"
                error={errors.name?.message}
                isRequired
                {...register('name')}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Tax ID / GSTIN"
              placeholder="Branch specific Tax ID"
              error={errors.tax_id?.message}
              {...register('tax_id')}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Phone"
                placeholder="+1..."
                error={errors.phone?.message}
                {...register('phone')}
              />
              <Input
                label="Email"
                type="email"
                placeholder="branch@company.com"
                error={errors.email?.message}
                {...register('email')}
              />
            </div>
          </div>

          <Input
            label="Address"
            placeholder="Branch physical address"
            error={errors.address?.message}
            {...register('address')}
          />

          <div className="flex items-center space-x-2 pt-2">
            <input
              type="checkbox"
              id="is_active"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active Branch
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Branch' : 'Create Branch'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default BranchForm;
