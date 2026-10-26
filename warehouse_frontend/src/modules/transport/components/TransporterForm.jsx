import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { transporterSchema } from '../schemas/transporter.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const defaultValues = {
  code: '',
  name: '',
  gstin: '',
  pan: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  state: '',
  pincode: '',
  vehicle_number: '',
  vehicle_type: '',
  driver_name: '',
  driver_phone: '',
};

const TransporterForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(transporterSchema),
    defaultValues,
  });

  useEffect(() => {
    if (initialData) {
      reset({
        code: initialData.code || '',
        name: initialData.name || '',
        gstin: initialData.gstin || '',
        pan: initialData.pan || '',
        contact_person: initialData.contact_person || '',
        phone: initialData.phone || '',
        email: initialData.email || '',
        address: initialData.address || '',
        city: initialData.city || '',
        state: initialData.state || '',
        pincode: initialData.pincode || '',
        vehicle_number: initialData.vehicle_number || '',
        vehicle_type: initialData.vehicle_type || '',
        driver_name: initialData.driver_name || '',
        driver_phone: initialData.driver_phone || '',
        status: initialData.status || 'ACTIVE',
      });
    }
  }, [initialData, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <Card.Header>
          <h2 className="text-base font-semibold text-gray-900">Transporter details</h2>
        </Card.Header>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Transporter Code"
              placeholder="TRN-001"
              error={errors.code?.message}
              isRequired
              {...register('code')}
              disabled={isEdit}
            />
            <Input
              label="Transporter Name"
              placeholder="VRL Logistics"
              error={errors.name?.message}
              isRequired
              {...register('name')}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="GSTIN" {...register('gstin')} error={errors.gstin?.message} />
            <Input label="PAN" {...register('pan')} error={errors.pan?.message} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Contact Person" {...register('contact_person')} />
            <Input label="Phone" {...register('phone')} error={errors.phone?.message} />
          </div>
          <Input label="Email" type="email" {...register('email')} error={errors.email?.message} />
          <Input label="Address" {...register('address')} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input label="City" {...register('city')} />
            <Input label="State" {...register('state')} />
            <Input label="PIN Code" {...register('pincode')} />
          </div>
          {isEdit && (
            <div className="max-w-xs">
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                {...register('status')}
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <h2 className="text-base font-semibold text-gray-900">Vehicle details (optional)</h2>
          <p className="text-sm text-gray-500 mt-1">
            Default vehicle and driver for this transporter — not a separate master list.
          </p>
        </Card.Header>
        <Card.Body className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Vehicle Number"
            placeholder="KA-01-AB-1234"
            {...register('vehicle_number')}
          />
          <Input label="Vehicle Type" placeholder="Truck / Tempo" {...register('vehicle_type')} />
          <Input label="Driver Name" {...register('driver_name')} />
          <Input label="Driver Phone" {...register('driver_phone')} />
        </Card.Body>
      </Card>

      <div className="flex justify-end gap-3">
        <Button type="submit" isLoading={isLoading}>
          {isEdit ? 'Save Changes' : 'Create Transporter'}
        </Button>
      </div>
    </form>
  );
};

export default TransporterForm;
