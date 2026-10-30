import React, { useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle } from 'lucide-react';
import { warehouseSchema } from '../schemas/warehouse.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { useCompanies } from '../../companies/hooks/use-companies';
import { useBranches } from '../../branches/hooks/use-branches';
import { useAuthStore } from '../../../store/auth.store';

const WarehouseForm = ({ 
  initialData, 
  onSubmit, 
  isLoading, 
  isEdit = false, 
  serverError = null 
}) => {
  const formRef = useRef(null);
  const { companyContext } = useAuthStore();
  const { data: companiesData } = useCompanies({ limit: 100 });

  const getFormDefaults = (data) => {
    if (data) {
      return {
        company_id: data.company_id || '',
        branch_id: data.branch_id || '',
        code: data.code || '',
        name: data.name || '',
        warehouse_type: data.warehouse_type || 'OWNED',
        address: data.address || data.address_line1 || '',
        city: data.city || '',
        state: data.state || '',
        contact_person: data.contact_person || '',
        phone: data.phone || '',
        is_active: data.is_active !== undefined ? Boolean(data.is_active) : (data.status ? data.status === 'ACTIVE' : true),
      };
    }
    return {
      company_id: companyContext || '',
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
    };
  };

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(warehouseSchema),
    defaultValues: getFormDefaults(initialData),
  });

  // Keep form in sync when initialData changes
  useEffect(() => {
    if (initialData) {
      reset(getFormDefaults(initialData));
    }
  }, [initialData, reset]);

  // If no company selected and we have company context or single company available, auto-set it
  const selectedCompanyId = watch('company_id');
  useEffect(() => {
    if (!selectedCompanyId) {
      if (companyContext) {
        setValue('company_id', companyContext);
      } else if (companiesData?.items?.length === 1) {
        setValue('company_id', companiesData.items[0].id);
      }
    }
  }, [selectedCompanyId, companyContext, companiesData, setValue]);

  const { data: branchesData } = useBranches(
    selectedCompanyId ? { company_id: selectedCompanyId, limit: 100 } : { limit: 100 }
  );

  const companies = useMemo(() => {
    return (companiesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [companiesData]);

  const branches = useMemo(() => {
    return (branchesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [branchesData]);

  const onError = () => {
    if (formRef.current) {
      formRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit(onSubmit, onError)} className="space-y-6">
      {serverError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-700 text-sm shadow-sm animate-in fade-in duration-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-red-800">Action Required</h4>
            <p className="mt-0.5 whitespace-pre-line">{serverError}</p>
          </div>
        </div>
      )}

      <Card>
        <Card.Body className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="company_id" className="text-sm font-medium text-gray-700">
                Company <span className="text-red-500">*</span>
              </label>
              <select
                id="company_id"
                {...register('company_id')}
                className={`w-full bg-white border rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition-all ${
                  errors.company_id ? 'border-red-500' : 'border-gray-200'
                }`}
                disabled={isEdit}
              >
                <option value="">Select Company</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name} ({company.code})
                  </option>
                ))}
              </select>
              {errors.company_id && (
                <p className="text-xs text-red-500 font-medium">{errors.company_id.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="branch_id" className="text-sm font-medium text-gray-700">
                Operating Branch <span className="text-xs text-gray-400 font-normal">(Optional)</span>
              </label>
              <select
                id="branch_id"
                {...register('branch_id')}
                className={`w-full bg-white border rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition-all ${
                  errors.branch_id ? 'border-red-500' : 'border-gray-200'
                }`}
                disabled={isEdit || !selectedCompanyId}
              >
                <option value="">None / Standalone Warehouse</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name} ({branch.code})
                  </option>
                ))}
              </select>
              {errors.branch_id && (
                <p className="text-xs text-red-500 font-medium">{errors.branch_id.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Warehouse Code"
              placeholder="e.g. WH-MUM-01"
              error={errors.code?.message}
              isRequired
              {...register('code')}
              disabled={isEdit}
              helperText={!isEdit ? 'Unique identifier code across the company' : undefined}
            />
            <Input
              label="Warehouse Name"
              placeholder="e.g. Mumbai Central Fulfillment Center"
              error={errors.name?.message}
              isRequired
              {...register('name')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="warehouse_type" className="text-sm font-medium text-gray-700">
                Type <span className="text-red-500">*</span>
              </label>
              <select
                id="warehouse_type"
                {...register('warehouse_type')}
                className={`w-full bg-white border rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none transition-all ${
                  errors.warehouse_type ? 'border-red-500' : 'border-gray-200'
                }`}
              >
                <option value="OWNED">Owned Facility</option>
                <option value="LEASED">Leased / Rented</option>
                <option value="BONDED">Bonded Warehouse</option>
                <option value="THIRD_PARTY">Third Party (3PL)</option>
                <option value="VENDOR">Supplier / Vendor Site</option>
                <option value="VIRTUAL">Virtual / In-Transit</option>
              </select>
              {errors.warehouse_type && (
                <p className="text-xs text-red-500 font-medium">{errors.warehouse_type.message}</p>
              )}
            </div>
            <Input
              label="City"
              placeholder="e.g. Mumbai"
              error={errors.city?.message}
              {...register('city')}
            />
            <Input
              label="State"
              placeholder="e.g. Maharashtra"
              error={errors.state?.message}
              {...register('state')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Contact Person"
              placeholder="e.g. Rajesh Sharma"
              error={errors.contact_person?.message}
              {...register('contact_person')}
            />
            <Input
              label="Phone Number"
              placeholder="e.g. +91 98765 43210"
              error={errors.phone?.message}
              {...register('phone')}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="address" className="text-sm font-medium text-gray-700">
              Detailed Facility Address
            </label>
            <textarea
              id="address"
              {...register('address')}
              className={`w-full bg-white border rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none min-h-[90px] transition-all ${
                errors.address ? 'border-red-500' : 'border-gray-200'
              }`}
              placeholder="Plot No, Industrial Estate, Sector / Landmark..."
            />
            {errors.address && (
              <p className="text-xs text-red-500 font-medium">{errors.address.message}</p>
            )}
          </div>

          <div className="pt-2 flex items-center space-x-2.5">
            <input
              type="checkbox"
              id="is_active"
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 transition-all cursor-pointer"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700 cursor-pointer select-none">
              Active Warehouse (Operational and available for inventory storage)
            </label>
          </div>
        </Card.Body>

        <Card.Footer className="flex justify-end items-center space-x-3 bg-gray-50/50">
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
