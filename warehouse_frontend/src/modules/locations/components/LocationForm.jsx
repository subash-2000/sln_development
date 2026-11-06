import React, { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { locationSchema } from '../schemas/location.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Card from '../../../components/ui/Card';
import { AlertCircle } from 'lucide-react';
import { useWarehouses } from '../../warehouses/hooks/use-warehouses';

const LOCATION_TYPE_OPTIONS = [
  { value: 'INTERNAL', label: 'Internal / storage' },
  { value: 'RECEIVING', label: 'Receiving' },
  { value: 'DISPATCH', label: 'Dispatch / shipping' },
  { value: 'TRANSIT', label: 'Transit' },
  { value: 'QUARANTINE', label: 'Quarantine' },
  { value: 'RETURN', label: 'Return' },
  { value: 'SCRAP', label: 'Scrap' },
  { value: 'STORAGE', label: 'Storage (legacy)' },
  { value: 'SHIPPING', label: 'Shipping (legacy)' },
  { value: 'PICKING', label: 'Picking (legacy)' },
  { value: 'VIRTUAL', label: 'Virtual (legacy)' },
];

const mapLocationToForm = (loc) => {
  if (!loc) return null;
  const statusActive = loc.is_active ?? (loc.status === 'ACTIVE');
  return {
    warehouse_id: loc.warehouse_id != null ? String(loc.warehouse_id) : '',
    code: loc.code ?? '',
    name: loc.name ?? '',
    location_type: loc.location_type || 'INTERNAL',
    zone: loc.zone ?? '',
    aisle: loc.aisle ?? '',
    shelf: loc.shelf ?? '',
    bin: loc.bin ?? '',
    is_active: Boolean(statusActive),
  };
};

const LocationForm = ({ initialData, onSubmit, isLoading, isEdit = false, serverError = null }) => {
  const { data: warehousesData } = useWarehouses();

  const warehouses = useMemo(() => {
    return (warehousesData?.items || []).slice().sort((a, b) =>
      (a.name || a.code || '').localeCompare(b.name || b.code || '', undefined, { numeric: true, sensitivity: 'base' })
    );
  }, [warehousesData]);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(locationSchema),
    defaultValues: mapLocationToForm(initialData) || {
      warehouse_id: '',
      code: '',
      name: '',
      location_type: 'INTERNAL',
      zone: '',
      aisle: '',
      shelf: '',
      bin: '',
      is_active: true,
    },
  });

  useEffect(() => {
    const mapped = mapLocationToForm(initialData);
    if (mapped) reset(mapped);
  }, [initialData, reset]);

  const warehouseId = watch('warehouse_id');
  const linkedWarehouse = useMemo(
    () => warehouses.find((wh) => String(wh.id) === String(warehouseId)),
    [warehouses, warehouseId],
  );

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {serverError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}
      <Card>
        <Card.Body className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="warehouse_id" className="text-sm font-medium text-gray-700">Warehouse</label>
              {isEdit ? (
                <>
                  <input type="hidden" {...register('warehouse_id')} />
                  <div
                    id="warehouse_id"
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-700"
                  >
                    {linkedWarehouse
                      ? `${linkedWarehouse.name} (${linkedWarehouse.code})`
                      : warehouseId
                        ? 'Warehouse linked (refresh list if name is missing)'
                        : '—'}
                  </div>
                  <p className="text-xs text-gray-500">Warehouse cannot be changed after a location is created.</p>
                </>
              ) : (
                <select
                  id="warehouse_id"
                  {...register('warehouse_id')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                >
                  <option value="">Select Warehouse</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={String(wh.id)}>{wh.name} ({wh.code})</option>
                  ))}
                </select>
              )}
              {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="location_type" className="text-sm font-medium text-gray-700">Location Type</label>
              <select
                id="location_type"
                {...register('location_type')}
                className="w-full bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none"
              >
                {LOCATION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
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
