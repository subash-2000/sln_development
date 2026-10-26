import React, { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { getCompanySchema } from '../schemas/company.schema';
import { useCompanies } from '../hooks/use-companies';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const getInitialValues = (data) => {
  if (!data) {
    return {
      code: '',
      name: '',
      legal_name: '',
      registration_number: '',
      tax_id: '',
      address: '',
      phone: '',
      email: '',
      website: '',
      is_active: true,
    };
  }
  return {
    code: data.code || '',
    name: data.name || '',
    legal_name: data.legal_name || '',
    registration_number: data.registration_number || '',
    tax_id: data.tax_id || data.gstin || '',
    address: data.address || '',
    phone: data.phone || '',
    email: data.email || '',
    website: data.website || '',
    is_active: data.is_active !== undefined ? Boolean(data.is_active) : (data.status === 'ACTIVE' || !data.status),
  };
};

const CompanyForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: companiesData } = useCompanies({ limit: 1000 });
  const existingCompanies = useMemo(() => {
    return companiesData?.items || (Array.isArray(companiesData) ? companiesData : []);
  }, [companiesData]);

  const currentCompanyId = initialData?.id || null;

  const schema = useMemo(
    () => getCompanySchema(isEdit, existingCompanies, currentCompanyId),
    [isEdit, existingCompanies, currentCompanyId]
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
      const match = existingCompanies.some(
        (c) => c.id !== currentCompanyId && c.code?.trim().toUpperCase() === clean.toUpperCase()
      );
      if (match) {
        setError('code', {
          type: 'manual',
          message: 'Company Code already exists with another company',
        });
      } else if (errors.code?.message === 'Company Code already exists with another company') {
        clearErrors('code');
      }
    } else if (fieldName === 'name') {
      const match = existingCompanies.some(
        (c) => c.id !== currentCompanyId && c.name?.trim().toLowerCase() === clean.toLowerCase()
      );
      if (match) {
        setError('name', {
          type: 'manual',
          message: 'Company Name already exists with another company',
        });
      } else if (errors.name?.message === 'Company Name already exists with another company') {
        clearErrors('name');
      }
    } else if (fieldName === 'registration_number') {
      const match = existingCompanies.some(
        (c) =>
          c.id !== currentCompanyId &&
          c.registration_number &&
          c.registration_number.trim().toLowerCase() === clean.toLowerCase()
      );
      if (match) {
        setError('registration_number', {
          type: 'manual',
          message: 'Registration Number already exists with another company',
        });
      } else if (
        errors.registration_number?.message ===
        'Registration Number already exists with another company'
      ) {
        clearErrors('registration_number');
      }
    } else if (fieldName === 'tax_id') {
      const match = existingCompanies.some(
        (c) =>
          c.id !== currentCompanyId &&
          (c.tax_id || c.gstin) &&
          (c.tax_id || c.gstin).trim().toUpperCase() === clean.toUpperCase()
      );
      if (match) {
        setError('tax_id', {
          type: 'manual',
          message: 'Tax ID / GSTIN already exists with another company',
        });
      } else if (
        errors.tax_id?.message === 'Tax ID / GSTIN already exists with another company'
      ) {
        clearErrors('tax_id');
      }
    }
  };

  const handleFormSubmit = (data) => {
    let hasConflict = false;

    const normalizedCode = data.code?.trim().toUpperCase();
    if (
      normalizedCode &&
      existingCompanies.some(
        (c) => c.id !== currentCompanyId && c.code?.trim().toUpperCase() === normalizedCode
      )
    ) {
      setError('code', {
        type: 'manual',
        message: 'Company Code already exists with another company',
      });
      hasConflict = true;
    }

    const normalizedName = data.name?.trim().toLowerCase();
    if (
      normalizedName &&
      existingCompanies.some(
        (c) => c.id !== currentCompanyId && c.name?.trim().toLowerCase() === normalizedName
      )
    ) {
      setError('name', {
        type: 'manual',
        message: 'Company Name already exists with another company',
      });
      hasConflict = true;
    }

    const normalizedReg = data.registration_number?.trim().toLowerCase();
    if (
      normalizedReg &&
      existingCompanies.some(
        (c) =>
          c.id !== currentCompanyId &&
          c.registration_number &&
          c.registration_number.trim().toLowerCase() === normalizedReg
      )
    ) {
      setError('registration_number', {
        type: 'manual',
        message: 'Registration Number already exists with another company',
      });
      hasConflict = true;
    }

    const normalizedTax = data.tax_id?.trim().toUpperCase();
    if (
      normalizedTax &&
      existingCompanies.some(
        (c) =>
          c.id !== currentCompanyId &&
          (c.tax_id || c.gstin) &&
          (c.tax_id || c.gstin).trim().toUpperCase() === normalizedTax
      )
    ) {
      setError('tax_id', {
        type: 'manual',
        message: 'Tax ID / GSTIN already exists with another company',
      });
      hasConflict = true;
    }

    if (hasConflict) {
      return;
    }

    const formattedData = {
      ...data,
      tax_id: data.tax_id ? data.tax_id.trim().toUpperCase() : '',
      phone: data.phone ? data.phone.trim() : '',
      address: data.address ? data.address.trim() : '',
    };
    onSubmit(formattedData, { setError });
  };

  const codeRegister = register('code');
  const nameRegister = register('name');
  const regNumRegister = register('registration_number');
  const taxIdRegister = register('tax_id');

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Company Code"
              placeholder="e.g. SLN"
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
              label="Company Name"
              placeholder="e.g. SLN Warehouse Solutions"
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
              label="Registration Number"
              placeholder="CIN/Reg No."
              error={errors.registration_number?.message}
              {...regNumRegister}
              onBlur={(e) => {
                regNumRegister.onBlur(e);
                checkDuplicate('registration_number', e.target.value);
              }}
            />
            <Input
              label="Tax ID / GSTIN"
              placeholder="Tax Identification Number"
              error={errors.tax_id?.message}
              isRequired
              {...taxIdRegister}
              onChange={(e) => {
                e.target.value = e.target.value.toUpperCase();
                taxIdRegister.onChange(e);
                if (errors.tax_id?.message === 'Tax ID / GSTIN already exists with another company') {
                  clearErrors('tax_id');
                }
              }}
              onBlur={(e) => {
                taxIdRegister.onBlur(e);
                checkDuplicate('tax_id', e.target.value);
              }}
            />
          </div>

          <Input
            label="Address"
            placeholder="Full registered address"
            error={errors.address?.message}
            isRequired
            {...register('address')}
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              label="Phone"
              placeholder="+1..."
              error={errors.phone?.message}
              isRequired
              {...register('phone')}
            />
            <Input
              label="Email"
              type="email"
              placeholder="contact@company.com"
              error={errors.email?.message}
              {...register('email')}
            />
            <Input
              label="Website"
              placeholder="https://..."
              error={errors.website?.message}
              {...register('website')}
            />
          </div>

          <div className="flex items-center space-x-2 pt-2">
            <input
              type="checkbox"
              id="is_active"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active Entity
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Company' : 'Create Company'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default CompanyForm;
