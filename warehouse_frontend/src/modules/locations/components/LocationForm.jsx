import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { locationSchema } from '../schemas/location.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';

const LocationForm = ({ initialData, onSubmit, isLoading, isEdit = false }) => {
  const { data: warehousesData } = useWarehouses();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(locationSchema),
    defaultValues: initialData || {
      warehouse_id: '',
      code: '',
      name: '',
      location_type: 'STORAGE',
      zone: '',
      aisle: '',
      shelf: '',
      bin: '',
      is_active: true,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="warehouse_id" className="text-sm font-medium text-gray-700">Warehouse</label>
              <select
                id="warehouse_id"
                {...register('warehouse_id')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                disabled={isEdit}
              >
                <option value="">Select Warehouse</option>
                {warehousesData?.items?.map(wh => (
                  <option key={wh.id} value={wh.id}>{wh.name} ({wh.code})</option>
                ))}
              </select>
              {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="location_type" className="text-sm font-medium text-gray-700">Location Type</label>
              <select
                id="location_type"
                {...register('location_type')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              >
                <option value="STORAGE">Storage</option>
                <option value="RECEIVING">Receiving</option>
                <option value="SHIPPING">Shipping</option>
                <option value="PICKING">Picking</option>
                <option value="VIRTUAL">Virtual</option>
              </select>
              {errors.location_type && <p className="text-xs text-red-500">{errors.location_type.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Location Code"
              placeholder="LOC-A-01-01"
              error={errors.code?.message}
              isRequired
              {...register('code')}
              disabled={isEdit}
            />
            <Input
              label="Location Name"
              placeholder="Aisle A - Shelf 1 - Bin 1"
              error={errors.name?.message}
              isRequired
              {...register('name')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Input label="Zone" placeholder="A" {...register('zone')} />
            <Input label="Aisle" placeholder="01" {...register('aisle')} />
            <Input label="Shelf" placeholder="01" {...register('shelf')} />
            <Input label="Bin" placeholder="01" {...register('bin')} />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_active"
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              {...register('is_active')}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active Location
            </label>
          </div>
        </Card.Body>
        <Card.Footer className="flex justify-end space-x-3">
          <Button type="button" variant="secondary" onClick={() => window.history.back()}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEdit ? 'Update Location' : 'Create Location'}
          </Button>
        </Card.Footer>
      </Card>
    </form>
  );
};

export default LocationForm;
