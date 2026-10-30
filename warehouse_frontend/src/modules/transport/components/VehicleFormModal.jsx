import React, { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { X, Truck, Building2, AlertCircle } from 'lucide-react';
import { vehicleSchema } from '../schemas/transporter.schema';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import { useTransporters, useAllVehicles } from '../hooks/use-transporters';
import { sortAscending } from '../../../utils/sort';

// Sorted in ascending alphabetical order
const RAW_VEHICLE_TYPE_PRESETS = [
  'Container 20ft',
  'Container 40ft',
  'Mini Truck',
  'Other',
  'Pickup',
  'Tanker',
  'Tempo',
  'Trailer',
  'Truck',
  'Van',
];

export const VEHICLE_TYPE_PRESETS = sortAscending(RAW_VEHICLE_TYPE_PRESETS);

const defaultValues = {
  vehicle_number: '',
  vehicle_type: 'Truck',
  driver_name: '',
  driver_phone: '',
  capacity: '',
  rc_number: '',
  is_default: false,
  status: 'ACTIVE',
};

const VehicleFormModal = ({
  open,
  onClose,
  onSubmit,
  initialData = null,
  transporterId = '',
  isLoading = false,
}) => {
  const isEdit = Boolean(initialData?.id);
  const [selectedTransporterId, setSelectedTransporterId] = useState(
    transporterId || initialData?.transporter_id || ''
  );
  const [transporterError, setTransporterError] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch all active transporters for selection dropdown
  const { data: transportersData, isLoading: isLoadingTransporters } = useTransporters({
    pageSize: 200,
    status: 'ACTIVE',
  });
  const rawTransporters = transportersData?.items || [];

  // Sort transporters in ascending alphabetical order
  const transporters = useMemo(() => {
    return sortAscending(rawTransporters, (t) => t.name || t.code);
  }, [rawTransporters]);

  // Fetch existing vehicles for instant client-side duplicate detection
  const { data: allVehiclesData } = useAllVehicles({ pageSize: 500 });

  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(vehicleSchema),
    defaultValues,
  });

  useEffect(() => {
    if (open) {
      const activeTransId =
        transporterId || initialData?.transporter_id || (transporters.length > 0 ? transporters[0].id : '');
      setSelectedTransporterId(activeTransId);
      setTransporterError('');
      setFormError('');

      if (initialData) {
        reset({
          vehicle_number: initialData.vehicle_number || '',
          vehicle_type: initialData.vehicle_type || 'Truck',
          driver_name: initialData.driver_name || '',
          driver_phone: initialData.driver_phone || '',
          capacity: initialData.capacity || '',
          rc_number: initialData.rc_number || '',
          is_default: Boolean(initialData.is_default),
          status: initialData.status || 'ACTIVE',
        });
      } else {
        reset(defaultValues);
      }
    }
  }, [open, initialData, transporterId, transporters.length, reset]);

  if (!open) return null;

  const handleFormSubmit = async (data) => {
    if (!selectedTransporterId) {
      setTransporterError('Please choose a transporter');
      return;
    }
    setTransporterError('');
    setFormError('');
    clearErrors('vehicle_number');

    const cleanInput = (data.vehicle_number || '').trim().toUpperCase();
    const compactInput = cleanInput.replace(/[^A-Z0-9]/g, '');

    // Instant client-side duplicate validation against registered vehicles
    const existingVehicles = allVehiclesData?.items || [];
    const duplicate = existingVehicles.find((v) => {
      if (isEdit && v.id === initialData?.id) return false;
      const vCompact = (v.vehicle_number || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
      return vCompact === compactInput;
    });

    if (duplicate) {
      const isSameTransporter = duplicate.transporter_id === selectedTransporterId;
      const transObj = transporters.find((t) => t.id === duplicate.transporter_id);
      const transName = duplicate.transporter_name || transObj?.name || 'this transporter';
      const msg = isSameTransporter
        ? `Vehicle '${cleanInput}' is already registered under this transporter.`
        : `Vehicle '${cleanInput}' is already registered under transporter '${transName}'.`;

      setError('vehicle_number', { type: 'manual', message: msg });
      setFormError(msg);
      return;
    }

    try {
      setIsSubmitting(true);
      await onSubmit({
        ...data,
        vehicle_number: cleanInput,
        transporter_id: selectedTransporterId,
      });
    } catch (err) {
      console.error('Vehicle form submission error:', err);
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to save vehicle. A vehicle with this registration number may already exist.';
      setFormError(msg);
      setError('vehicle_number', { type: 'manual', message: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentTransporter = transporters.find((t) => t.id === selectedTransporterId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <button
        type="button"
        className="absolute inset-0 bg-gray-900/50 backdrop-blur-xs transition-opacity"
        aria-label="Close dialog"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[92vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-blue-50/60 to-indigo-50/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <Truck size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900">
                {isEdit ? 'Edit Vehicle' : 'Add Vehicle to Transport Master'}
              </h2>
              <p className="text-xs text-gray-500">
                Vehicle numbers are inter-linked with their respective transporter
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit(handleFormSubmit)} className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Server / Validation Error Alert */}
          {formError && (
            <div className="flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs shadow-2xs">
              <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium">{formError}</div>
              <button
                type="button"
                onClick={() => setFormError('')}
                className="text-red-400 hover:text-red-600 text-xs font-semibold ml-2"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Transporter Selection Dropdown */}
          <div className="bg-blue-50/40 border border-blue-100 rounded-xl p-3.5 space-y-1.5">
            <label className="block text-xs font-semibold text-blue-900 uppercase tracking-wider flex items-center gap-1.5">
              <Building2 size={14} className="text-blue-600" />
              <span>Choose Transporter / Carrier</span>
              <span className="text-red-500">*</span>
            </label>

            {isLoadingTransporters ? (
              <div className="text-xs text-gray-500 py-1">Loading transporters...</div>
            ) : transporters.length === 0 ? (
              <div className="text-xs text-amber-700 py-1">
                No active transporters found. Please create a transporter first.
              </div>
            ) : (
              <select
                value={selectedTransporterId}
                onChange={(e) => {
                  setSelectedTransporterId(e.target.value);
                  if (e.target.value) setTransporterError('');
                  setFormError('');
                  clearErrors('vehicle_number');
                }}
                disabled={isEdit}
                className="w-full border border-blue-200 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-2xs"
              >
                <option value="">-- Select a Transporter --</option>
                {transporters.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.code})
                  </option>
                ))}
              </select>
            )}

            {transporterError && (
              <p className="text-xs text-red-600 font-medium">{transporterError}</p>
            )}

            {currentTransporter && (
              <div className="text-[11px] text-gray-500 flex items-center gap-2 pt-0.5">
                <span>Code: <b className="text-gray-700">{currentTransporter.code}</b></span>
                {currentTransporter.gstin && (
                  <span>• GSTIN: <b className="text-gray-700">{currentTransporter.gstin}</b></span>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Vehicle Registration No."
              placeholder="e.g. KA-01-AB-1234"
              isRequired
              error={errors.vehicle_number?.message}
              {...register('vehicle_number', {
                setValueAs: (v) => (v ? v.trim().toUpperCase() : ''),
                onChange: () => {
                  if (formError) setFormError('');
                  clearErrors('vehicle_number');
                },
              })}
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Vehicle Type
              </label>
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                {...register('vehicle_type')}
              >
                {VEHICLE_TYPE_PRESETS.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Driver Name"
              placeholder="e.g. Ramesh Kumar"
              error={errors.driver_name?.message}
              {...register('driver_name')}
            />
            <Input
              type="tel"
              label="Driver Phone"
              placeholder="e.g. +91 98765 43210"
              error={errors.driver_phone?.message}
              {...register('driver_phone', {
                onChange: (e) => {
                  // Strictly block letters: allow digits, optional leading +, space, hyphen
                  const filtered = e.target.value.replace(/[^0-9+\s-]/g, '');
                  if (filtered !== e.target.value) {
                    e.target.value = filtered;
                  }
                },
              })}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Capacity / Tonnage"
              placeholder="e.g. 10 Ton / 32 Ft"
              error={errors.capacity?.message}
              {...register('capacity')}
            />
            <Input
              label="RC / Permit Number"
              placeholder="e.g. RC98765432"
              error={errors.rc_number?.message}
              {...register('rc_number')}
            />
          </div>

          <div className="pt-2 border-t border-gray-100 flex items-center justify-end">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-medium">Status:</span>
              <select
                className="text-xs font-medium border border-gray-300 rounded-md px-2 py-1 bg-white"
                {...register('status')}
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-gray-100 flex justify-end gap-2.5">
            <Button
              variant="secondary"
              type="button"
              onClick={onClose}
              disabled={isLoading || isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading || isSubmitting}>
              {isEdit ? 'Save Changes' : 'Add Vehicle'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default VehicleFormModal;
