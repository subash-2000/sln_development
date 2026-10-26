import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { warehouseSchema } from '../schemas/warehouse.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { useCompanies } from '../../companies/hooks/use-companies';
import { useBranches } from '../../branches/hooks/use-branches';

const WarehouseForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: companiesData } = useCompanies();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(warehouseSchema),
    defaultValues: initialData || {
      company_id: '',
      branch_id: '',
      code: '',
      name: '',
      warehouse_type: 'OWNED',
      address: '',
      city: '',
      state: '',
      contact_person: '',
      phone: '',
      is_active: true,
    },
  });

  const selectedCompanyId = watch('company_id');
  const { data: branchesData } = useBranches({ company_id: selectedCompanyId });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="company_id" className="text-sm font-medium text-gray-700">Company</label>
              <select
                id="company_id"
                {...register('company_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                disabled={isEdit}
              >
                <option value="">Select Company</option>
                {companiesData?.items?.map(company => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
              {errors.company_id && <p className="text-xs text-red-500">{errors.company_id.message}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="branch_id" className="text-sm font-medium text-gray-700">Branch</label>
              <select
                id="branch_id"
                {...register('branch_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                disabled={isEdit || !selectedCompanyId}
              >
                <option value="">Select Branch</option>
                {branchesData?.items?.map(branch => (
                  <option key={branch.id} value={branch.id}>{branch.name}</option>
                ))}
              </select>
              {errors.branch_id && <p className="text-xs text-red-500">{errors.branch_id.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Warehouse Code"
              placeholder="WH-001"
              error={errors.code?.message}
              isRequired
              {...register('code')}
              disabled={isEdit}
            />
            <Input
              label="Warehouse Name"
              placeholder="Central Logistics Hub"
              error={errors.name?.message}
              isRequired
              {...register('name')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="warehouse_type" className="text-sm font-medium text-gray-700">Type</label>
              <select
                id="warehouse_type"
                {...register('warehouse_type')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="OWNED">Owned</option>
                <option value="LEASED">Leased</option>
                <option value="VENDOR">Supplier site</option>
              </select>
              {errors.warehouse_type && <p className="text-xs text-red-500">{errors.warehouse_type.message}</p>}
            </div>
            <Input
              label="City"
              placeholder="Mumbai"
              error={errors.city?.message}
              isRequired
              {...register('city')}
            />
            <Input
              label="State"
              placeholder="Maharashtra"
              error={errors.state?.message}
              isRequired
              {...register('state')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Contact Person"
              placeholder="Robert Manager"
              error={errors.contact_person?.message}
              {...register('contact_person')}
            />
            <Input
              label="Phone Number"
              placeholder="+91 99999 88888"
              error={errors.phone?.message}
              {...register('phone')}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="address" className="text-sm font-medium text-gray-700">Detailed Address</label>
            <textarea
              id="address"
              {...register('address')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none min-h-[80px]"
              placeholder="Plot No, Industrial Area, Near Landmark..."
            />
            {errors.address && <p className="text-xs text-red-500">{errors.address.message}</p>}
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_active"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active Warehouse
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Warehouse' : 'Create Warehouse'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default WarehouseForm;
