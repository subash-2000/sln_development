import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { customerSchema } from '../schemas/customer.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';

const CustomerForm = ({ initialData, onSubmit, isLoading, isEdit = false, mode = 'customer' }) => {
  const isBuyer = mode === 'buyer';
  const noun = isBuyer ? 'Buyer' : 'Customer';
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(customerSchema),
    defaultValues: initialData || {
      code: '',
      name: '',
      gstin: '',
      contact_person: '',
      phone: '',
      email: '',
      address: '',
      is_active: true,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label={`${noun} Code`}
              placeholder={isBuyer ? 'BUY001' : 'CUS001'}
              error={errors.code?.message}
              isRequired
              {...register('code')}
              disabled={isEdit}
            />
            <Input
              label={`${noun} Name`}
              placeholder={isBuyer ? 'SKF India Limited' : 'Global Traders'}
              error={errors.name?.message}
              isRequired
              {...register('name')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="GSTIN"
              placeholder="29ABCDE1234F1Z5"
              error={errors.gstin?.message}
              {...register('gstin')}
            />
            <Input
              label="Contact Person"
              placeholder="Jane Smith"
              error={errors.contact_person?.message}
              {...register('contact_person')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Phone Number"
              placeholder="+91 98765 43210"
              error={errors.phone?.message}
              {...register('phone')}
            />
            <Input
              label="Email Address"
              type="email"
              placeholder="customer@example.com"
              error={errors.email?.message}
              {...register('email')}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="address" className="text-sm font-medium text-gray-700">Billing Address</label>
            <textarea
              id="address"
              {...register('address')}
              className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none min-h-[100px]"
              placeholder="Full billing address..."
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
              Active {noun}
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? `Update ${noun}` : `Create ${noun}`}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default CustomerForm;
