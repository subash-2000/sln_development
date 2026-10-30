import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { createUserSchema, editUserSchema } from '../schemas/user.schema';
import { useRoles } from '../../roles/hooks/use-roles';
import { useCompanies } from '../../companies/hooks/use-companies';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const getInitialUserValues = (data) => {
  if (!data) {
    return {
      username: '',
      email: '',
      name: '',
      password: '',
      role_id: '',
      company_ids: [],
      is_active: true,
    };
  }
  return {
    username: data.username || '',
    email: data.email || '',
    name: data.full_name || data.name || '',
    password: '',
    role_id: data.role_id || data.roles?.[0]?.id || (Array.isArray(data.role_ids) ? data.role_ids[0] : '') || '',
    company_ids: data.company_ids || data.companies?.map((c) => c.id) || (data.tenants?.map((t) => t.company_id) || []),
    is_active: data.is_active !== undefined ? Boolean(data.is_active) : (data.status === 'ACTIVE' || !data.status),
  };
};

const UserForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: rolesData } = useRoles();
  const { data: companiesData } = useCompanies({ page_size: 100 });

  const fetchedRoles = rolesData?.items || (Array.isArray(rolesData) ? rolesData : []);
  const fetchedCompanies = companiesData?.items || (Array.isArray(companiesData) ? companiesData : []);

  const defaultRoles = [
    { id: 'role_1', name: 'Super Admin' },
    { id: 'role_2', name: 'Manager' },
    { id: 'role_3', name: 'Operator' },
  ];
  const defaultCompanies = [
    { id: 'cmp_1', name: 'Company Alpha' },
    { id: 'cmp_2', name: 'Company Beta' },
  ];

  const roles = React.useMemo(() => {
    const list = fetchedRoles.length > 0 ? fetchedRoles : defaultRoles;
    return list.slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [fetchedRoles]);

  const companies = React.useMemo(() => {
    const list = fetchedCompanies.length > 0 ? fetchedCompanies : defaultCompanies;
    return list.slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [fetchedCompanies]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(isEdit ? editUserSchema : createUserSchema),
    defaultValues: getInitialUserValues(initialData),
  });

  useEffect(() => {
    if (initialData) {
      reset(getInitialUserValues(initialData));
    }
  }, [initialData, reset]);

  const handleFormSubmit = (data) => {
    const payload = {
      ...data,
      name: data.name,
      full_name: data.name,
      role_ids: data.role_id ? [data.role_id] : (data.role_ids || []),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Username"
              placeholder="johndoe"
              error={errors.username?.message}
              isRequired
              {...register('username')}
              disabled={isEdit}
            />
            <Input
              label="Email Address"
              type="email"
              placeholder="john@example.com"
              error={errors.email?.message}
              isRequired
              {...register('email')}
            />
          </div>

          <Input
            label="Full Name"
            placeholder="John Doe"
            error={errors.name?.message}
            isRequired
            {...register('name')}
          />

          {!isEdit && (
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              isRequired
              {...register('password')}
            />
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="role_id" className="text-sm font-medium text-gray-700">Role</label>
              <select
                id="role_id"
                {...register('role_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="">Select a role</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              {errors.role_id && <p className="text-xs text-red-500">{errors.role_id.message}</p>}
            </div>

            <div className="flex items-center space-x-2 pt-8">
              <input
                type="checkbox"
                id="is_active"
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                {...register('is_active')}
              />
              <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                Account Active
              </label>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Assigned Companies</label>
            <div className="flex flex-wrap gap-3 p-3 border border-gray-200 rounded-lg bg-gray-50 max-h-48 overflow-y-auto">
              {companies.map((c) => (
                <label key={c.id} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    value={c.id}
                    {...register('company_ids')}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">{c.name}</span>
                </label>
              ))}
            </div>
            {errors.company_ids && <p className="text-xs text-red-500">{errors.company_ids.message}</p>}
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update User' : 'Create User'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default UserForm;
