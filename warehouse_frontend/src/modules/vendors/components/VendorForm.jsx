import React, { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { getSupplierSchema } from '../schemas/vendor.schema';
import { useVendors } from '../hooks/use-vendors';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const getInitialValues = (data) => {
  if (!data) {
    return {
      code: '',
      name: '',
      gstin: '',
      contact_person: '',
      phone: '',
      email: '',
      address: '',
      invoice_workflow: 'STANDARD',
      is_active: true,
    };
  }
  return {
    code: data.code || '',
    name: data.name || '',
    gstin: data.gstin || '',
    contact_person: data.contact_person || '',
    phone: data.phone || '',
    email: data.email || '',
    address: data.address || data.billing_address || '',
    invoice_workflow: data.invoice_workflow || 'STANDARD',
    is_active:
      data.is_active !== undefined
        ? Boolean(data.is_active)
        : data.status === 'ACTIVE' || !data.status,
  };
};

const VendorForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: vendorsData } = useVendors({ limit: 1000 });
  const existingVendors = useMemo(() => {
    return vendorsData?.items || (Array.isArray(vendorsData) ? vendorsData : []);
  }, [vendorsData]);

  const currentVendorId = initialData?.id || null;

  const schema = useMemo(
    () => getSupplierSchema(isEdit, existingVendors, currentVendorId),
    [isEdit, existingVendors, currentVendorId]
  );

  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: getInitialValues(initialData),
    mode: 'onTouched',
  });

  useEffect(() => {
    if (initialData) {
      reset(getInitialValues(initialData));
    }
  }, [initialData, reset, isEdit]);

  const checkDuplicate = (fieldName, value) => {
    if (!value || typeof value !== 'string') return;
    const clean = value.trim();
    if (!clean) return;

    if (fieldName === 'code') {
      const match = existingVendors.some(
        (v) => v.id !== currentVendorId && v.code?.trim().toUpperCase() === clean.toUpperCase()
      );
      if (match) {
        setError('code', {
          type: 'manual',
          message: 'Supplier Code already exists with another supplier',
        });
      } else if (errors.code?.message === 'Supplier Code already exists with another supplier') {
        clearErrors('code');
      }
    } else if (fieldName === 'name') {
      const match = existingVendors.some(
        (v) => v.id !== currentVendorId && v.name?.trim().toLowerCase() === clean.toLowerCase()
      );
      if (match) {
        setError('name', {
          type: 'manual',
          message: 'Supplier Name already exists with another supplier',
        });
      } else if (errors.name?.message === 'Supplier Name already exists with another supplier') {
        clearErrors('name');
      }
    } else if (fieldName === 'gstin') {
      const match = existingVendors.some(
        (v) =>
          v.id !== currentVendorId &&
          v.gstin &&
          v.gstin.trim().toUpperCase() === clean.toUpperCase()
      );
      if (match) {
        setError('gstin', {
          type: 'manual',
          message: 'GSTIN already exists with another supplier',
        });
      } else if (errors.gstin?.message === 'GSTIN already exists with another supplier') {
        clearErrors('gstin');
      }
    } else if (fieldName === 'phone') {
      const compactClean = clean.replace(/[\s-]/g, '');
      const match = existingVendors.some(
        (v) =>
          v.id !== currentVendorId &&
          v.phone &&
          v.phone.trim().replace(/[\s-]/g, '') === compactClean
      );
      if (match) {
        setError('phone', {
          type: 'manual',
          message: 'Phone number already exists with another supplier',
        });
      } else if (errors.phone?.message === 'Phone number already exists with another supplier') {
        clearErrors('phone');
      }
    }
  };

  const handleFormSubmit = (data) => {
    let hasConflict = false;

    const normalizedCode = data.code?.trim().toUpperCase();
    if (
      normalizedCode &&
      existingVendors.some(
        (v) => v.id !== currentVendorId && v.code?.trim().toUpperCase() === normalizedCode
      )
    ) {
      setError('code', {
        type: 'manual',
        message: 'Supplier Code already exists with another supplier',
      });
      hasConflict = true;
    }

    const normalizedName = data.name?.trim().toLowerCase();
    if (
      normalizedName &&
      existingVendors.some(
        (v) => v.id !== currentVendorId && v.name?.trim().toLowerCase() === normalizedName
      )
    ) {
      setError('name', {
        type: 'manual',
        message: 'Supplier Name already exists with another supplier',
      });
      hasConflict = true;
    }

    const normalizedGstin = data.gstin?.trim().toUpperCase();
    if (
      normalizedGstin &&
      existingVendors.some(
        (v) =>
          v.id !== currentVendorId &&
          v.gstin &&
          v.gstin.trim().toUpperCase() === normalizedGstin
      )
    ) {
      setError('gstin', {
        type: 'manual',
        message: 'GSTIN already exists with another supplier',
      });
      hasConflict = true;
    }

    const normalizedPhone = data.phone?.trim().replace(/[\s-]/g, '');
    if (
      normalizedPhone &&
      existingVendors.some(
        (v) =>
          v.id !== currentVendorId &&
          v.phone &&
          v.phone.trim().replace(/[\s-]/g, '') === normalizedPhone
      )
    ) {
      setError('phone', {
        type: 'manual',
        message: 'Phone number already exists with another supplier',
      });
      hasConflict = true;
    }

    if (hasConflict) {
      return;
    }

    const formattedData = {
      ...data,
      gstin: data.gstin ? data.gstin.trim().toUpperCase() : '',
      phone: data.phone ? data.phone.trim() : '',
      address: data.address ? data.address.trim() : '',
    };
    onSubmit(formattedData, { setError });
  };

  const codeRegister = register('code');
  const nameRegister = register('name');
  const gstinRegister = register('gstin');
  const phoneRegister = register('phone');

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Supplier Code"
              placeholder="VND001"
              error={errors.code?.message}
              isRequired
              disabled={isEdit}
              {...codeRegister}
              onBlur={(e) => {
                codeRegister.onBlur(e);
                checkDuplicate('code', e.target.value);
              }}
            />
            <Input
              label="Supplier Name"
              placeholder="Acme Supplies"
              error={errors.name?.message}
              isRequired
              {...nameRegister}
              onBlur={(e) => {
                nameRegister.onBlur(e);
                checkDuplicate('name', e.target.value);
              }}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="GSTIN"
              placeholder="Tax Identification Number"
              error={errors.gstin?.message}
              isRequired
              {...gstinRegister}
              onChange={(e) => {
                e.target.value = e.target.value.toUpperCase();
                gstinRegister.onChange(e);
                if (errors.gstin?.message === 'GSTIN already exists with another supplier') {
                  clearErrors('gstin');
                }
              }}
              onBlur={(e) => {
                gstinRegister.onBlur(e);
                checkDuplicate('gstin', e.target.value);
              }}
            />
            <Input
              label="Contact Person"
              placeholder="John Doe"
              error={errors.contact_person?.message}
              {...register('contact_person')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Phone Number"
              placeholder="+1..."
              error={errors.phone?.message}
              isRequired
              {...phoneRegister}
              onChange={(e) => {
                phoneRegister.onChange(e);
                if (errors.phone?.message === 'Phone number already exists with another supplier') {
                  clearErrors('phone');
                }
              }}
              onBlur={(e) => {
                phoneRegister.onBlur(e);
                checkDuplicate('phone', e.target.value);
              }}
            />
            <Input
              label="Email Address"
              type="email"
              placeholder="supplier@example.com"
              error={errors.email?.message}
              {...register('email')}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="address" className="text-sm font-medium text-gray-700">
              Address <span className="text-red-500">*</span>
            </label>
            <textarea
              id="address"
              {...register('address')}
              className={`w-full bg-white border ${
                errors.address ? 'border-red-500 focus:ring-red-500' : 'border-gray-200 focus:ring-primary-500'
              } rounded-lg px-4 py-2 text-sm focus:ring-2 outline-none min-h-[100px]`}
              placeholder="Full office/warehouse address..."
            />
            {errors.address && <p className="text-xs text-red-500">{errors.address.message}</p>}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="invoice_workflow" className="text-sm font-medium text-gray-700">
              Invoice workflow
            </label>
            <select
              id="invoice_workflow"
              {...register('invoice_workflow')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
            >
              <option value="STANDARD">Standard</option>
              <option value="JOB_WORK">Job Work (no GST, SLN delivery challan)</option>
              <option value="DIRECT_INVOICE">Direct Invoice (supplier invoices customer)</option>
              <option value="BOTH">Both (Pushp — choose per transaction)</option>
            </select>
            <p className="text-xs text-gray-500">
              Job Work never generates an SLN tax invoice. Direct Invoice records the supplier invoice only.
            </p>
          </div>

          <div className="flex items-center space-x-2 pt-2">
            <input
              type="checkbox"
              id="is_active"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active Supplier
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Supplier' : 'Create Supplier'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default VendorForm;
