import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ChevronDown } from 'lucide-react';
import { productSchema } from '../schemas/product.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { useCategories, useUOMs } from '../hooks/use-products';
import { PACKAGE_TRACKING_TYPES } from '../constants/trackingDimensions';
import { useCompanies } from '../../companies/hooks/use-companies';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useAuthStore } from '../../../store/auth.store';

const compactInputClass = 'h-9 py-1.5 px-3 rounded-md';
const compactSelectClass =
  'w-full h-9 bg-white border border-gray-200 rounded-md px-3 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none disabled:bg-gray-50';
const fieldGridClass = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3';

const ProductForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { companyContext } = useAuthStore();
  const { data: companiesData } = useCompanies({ page_size: 50 });
  const companies = companiesData?.items || [];
  const { data: categoriesData } = useCategories();
  const { data: uomsData } = useUOMs();
  const { data: vendorsData } = useVendors({ page_size: 200, status: 'ACTIVE' });
  const vendors = vendorsData?.items || [];

  const defaultValues = useMemo(() => {
    if (!initialData) {
      return {
        company_id: companyContext || (companies[0]?.id ?? ''),
        sku: '',
        name: '',
        part_number: '',
        description: '',
        category_id: '',
        uom_id: '',
        hsn_code: '',
        net_weight: '',
        batch_number: '',
        heat_number: '',
        gauge_number: '',
        mill_name: '',
        package_tracking_type: '',
        package_tracking_value: '',
        packing_ratio: '',
        is_lot_tracked: false,
        is_active: true,
        vendor_ids: [],
      };
    }
    return {
      company_id: initialData.company_id || companyContext || '',
      sku: initialData.sku || '',
      name: initialData.name || '',
      part_number: initialData.part_number || '',
      description: initialData.description || '',
      category_id: initialData.category_id || '',
      uom_id: initialData.uom_id || '',
      hsn_code: initialData.hsn_code || '',
      net_weight: initialData.net_weight ?? '',
      batch_number: initialData.batch_number || '',
      heat_number: initialData.heat_number || '',
      gauge_number: initialData.gauge_number || '',
      mill_name: initialData.mill_name || '',
      package_tracking_type: initialData.package_tracking_type || '',
      package_tracking_value: initialData.package_tracking_value || '',
      packing_ratio: initialData.packing_ratio || '',
      is_lot_tracked: initialData.is_lot_tracked ?? false,
      is_active: initialData.is_active ?? (initialData.status === 'ACTIVE'),
      vendor_ids: (initialData.vendor_ids || []).map((id) => String(id)),
    };
  }, [initialData, companyContext, companies]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(productSchema),
    defaultValues,
    values: defaultValues,
  });

  const packageTrackingType = watch('package_tracking_type');
  const selectedVendorIds = (watch('vendor_ids') || []).map(String);
  const selectedPackageType = PACKAGE_TRACKING_TYPES.find((d) => d.value === packageTrackingType);
  const [supplierMenuOpen, setSupplierMenuOpen] = useState(false);
  const supplierMenuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (supplierMenuRef.current && !supplierMenuRef.current.contains(event.target)) {
        setSupplierMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedVendorNames = vendors
    .filter((vendor) => selectedVendorIds.includes(String(vendor.id)))
    .map((vendor) => vendor.name);

  const toggleVendor = (vendorId) => {
    const id = String(vendorId);
    const next = selectedVendorIds.includes(id)
      ? selectedVendorIds.filter((value) => value !== id)
      : [...selectedVendorIds, id];
    setValue('vendor_ids', next, { shouldDirty: true, shouldValidate: true });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 w-full">
      <Card className="w-full">
        <Card.Body className="space-y-3 w-full">
          {companies.length > 1 && !isEdit && (
            <div className="space-y-1 sm:max-w-md">
              <label htmlFor="company_id" className="text-sm font-medium text-gray-700">Company</label>
              <select
                id="company_id"
                {...register('company_id')}
                className={compactSelectClass}
              >
                <option value="">Select Company (Defaults to active context)</option>
                {companies.map(c => (
                  <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                ))}
              </select>
              {errors.company_id && <p className="text-xs text-red-500">{errors.company_id.message}</p>}
            </div>
          )}

          <div className={fieldGridClass}>
            <Input
              label="SKU"
              placeholder="SKU-001"
              error={errors.sku?.message}
              isRequired
              className={compactInputClass}
              {...register('sku')}
              disabled={isEdit}
            />
            <Input
              label="Product Name"
              placeholder="Widget Alpha"
              error={errors.name?.message}
              isRequired
              className={compactInputClass}
              {...register('name')}
            />
            <Input
              label="Part Number"
              placeholder="Part no."
              error={errors.part_number?.message}
              className={compactInputClass}
              {...register('part_number')}
            />
            <div className="space-y-1">
              <label htmlFor="category_id" className="text-sm font-medium text-gray-700">Category</label>
              <select
                id="category_id"
                {...register('category_id')}
                className={compactSelectClass}
              >
                <option value="">Select Category (Optional)</option>
                {categoriesData?.items?.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
              {errors.category_id && <p className="text-xs text-red-500">{errors.category_id.message}</p>}
            </div>

            <div className="space-y-1">
              <label htmlFor="uom_id" className="text-sm font-medium text-gray-700">UOM</label>
              <select
                id="uom_id"
                {...register('uom_id')}
                className={compactSelectClass}
              >
                <option value="">Select UOM</option>
                {uomsData?.map(uom => (
                  <option key={uom.id} value={uom.id}>{uom.name} ({uom.code})</option>
                ))}
              </select>
              {errors.uom_id && <p className="text-xs text-red-500">{errors.uom_id.message}</p>}
            </div>

            <div className="space-y-1" ref={supplierMenuRef}>
              <label htmlFor="vendor_ids" className="text-sm font-medium text-gray-700">
                Suppliers <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <button
                  id="vendor_ids"
                  type="button"
                  onClick={() => setSupplierMenuOpen((open) => !open)}
                  className={`${compactSelectClass} flex items-center justify-between text-left`}
                >
                  <span className={selectedVendorNames.length ? 'truncate text-gray-900' : 'truncate text-gray-400'}>
                    {selectedVendorNames.length
                      ? selectedVendorNames.join(', ')
                      : 'Select suppliers'}
                  </span>
                  <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />
                </button>
                {supplierMenuOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg max-h-56 overflow-y-auto">
                    {vendors.length === 0 && (
                      <p className="px-3 py-2 text-xs text-gray-500">No suppliers in master yet.</p>
                    )}
                    {vendors.map((vendor) => {
                      const checked = selectedVendorIds.includes(String(vendor.id));
                      return (
                        <button
                          key={vendor.id}
                          type="button"
                          onClick={() => toggleVendor(vendor.id)}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-800 hover:bg-gray-50"
                        >
                          <span
                            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                              checked
                                ? 'border-primary-600 bg-primary-600 text-white'
                                : 'border-gray-300 bg-white'
                            }`}
                          >
                            {checked ? '✓' : ''}
                          </span>
                          <span>{vendor.name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              {errors.vendor_ids && (
                <p className="text-xs text-red-500">{errors.vendor_ids.message}</p>
              )}
            </div>

            <Input
              label="HSN Code"
              placeholder="84818030"
              error={errors.hsn_code?.message}
              className={compactInputClass}
              {...register('hsn_code')}
            />
            <Input
              label="Per ring weight (kg)"
              type="text"
              inputMode="decimal"
              placeholder="0.063"
              helperText="Fixed weight used on rings inward / dispatch"
              error={errors.net_weight?.message}
              className={compactInputClass}
              {...register('net_weight')}
            />
            <Input
              label="Packing ratio"
              placeholder="2+1+1"
              helperText="Default packing mix, filled from inward PDF when empty"
              error={errors.packing_ratio?.message}
              className={compactInputClass}
              {...register('packing_ratio')}
            />
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-6">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_lot_tracked"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  {...register('is_lot_tracked')}
                />
                <label htmlFor="is_lot_tracked" className="text-sm font-medium text-gray-700">
                  Lot Tracked
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  {...register('is_active')}
                />
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                  Active Product
                </label>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-100 bg-gray-50/80 p-3 space-y-3 w-full">
            <div>
              <p className="text-sm font-medium text-gray-800">Tracking (lot / batch)</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Batch, heat, gauge, mill, and pallet or cotton box identifiers.
              </p>
            </div>
            <div className={fieldGridClass}>
              <Input
                label="Batch number"
                placeholder="Batch no."
                error={errors.batch_number?.message}
                className={compactInputClass}
                {...register('batch_number')}
              />
              <Input
                label="Heat number"
                placeholder="Heat no."
                error={errors.heat_number?.message}
                className={compactInputClass}
                {...register('heat_number')}
              />
              <Input
                label="Gauge number"
                placeholder="Gauge no."
                error={errors.gauge_number?.message}
                className={compactInputClass}
                {...register('gauge_number')}
              />
              <Input
                label="Mill name"
                placeholder="Mill name"
                error={errors.mill_name?.message}
                className={compactInputClass}
                {...register('mill_name')}
              />
              <div className="space-y-1">
                <label htmlFor="package_tracking_type" className="text-sm font-medium text-gray-700">
                  Pallet or cotton box
                </label>
                <select
                  id="package_tracking_type"
                  {...register('package_tracking_type')}
                  className={compactSelectClass}
                >
                  <option value="">None</option>
                  {PACKAGE_TRACKING_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                {errors.package_tracking_type && (
                  <p className="text-xs text-red-500">{errors.package_tracking_type.message}</p>
                )}
              </div>
              <Input
                label={selectedPackageType ? selectedPackageType.label : 'Number'}
                placeholder={
                  selectedPackageType
                    ? `Enter ${selectedPackageType.label.toLowerCase()}`
                    : 'Select type first'
                }
                disabled={!packageTrackingType}
                error={errors.package_tracking_value?.message}
                className={compactInputClass}
                {...register('package_tracking_value')}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="description" className="text-sm font-medium text-gray-700">Description</label>
            <textarea
              id="description"
              {...register('description')}
              className="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none min-h-[72px] resize-y"
              placeholder="Technical specifications or notes..."
            />
            {errors.description && <p className="text-xs text-red-500">{errors.description.message}</p>}
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Product' : 'Create Product'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default ProductForm;
