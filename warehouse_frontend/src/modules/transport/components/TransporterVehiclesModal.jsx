import React, { useState } from 'react';
import { X, Plus, Truck, Phone, User, Edit2, Trash2, Search } from 'lucide-react';
import Button from '../../../components/ui/Button';
import Badge from '../../../components/ui/Badge';
import StatusBadge from '../../../components/ui/StatusBadge';
import ConfirmDialog from '../../../components/modals/ConfirmDialog';
import VehicleFormModal from './VehicleFormModal';
import {
  useTransporterVehicles,
  useCreateVehicle,
  useUpdateVehicle,
  useDeleteVehicle,
} from '../hooks/use-transporters';

const TransporterVehiclesModal = ({ open, onClose, transporter }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [deletingVehicle, setDeletingVehicle] = useState(null);

  const transporterId = transporter?.id;
  const { data, isLoading, refetch } = useTransporterVehicles(transporterId, {
    search: searchTerm || undefined,
    pageSize: 100,
  });

  const { mutateAsync: createVehicle, isPending: isCreating } = useCreateVehicle(transporterId);
  const { mutateAsync: updateVehicle, isPending: isUpdating } = useUpdateVehicle(transporterId);
  const { mutateAsync: deleteVehicle, isPending: isDeleting } = useDeleteVehicle(transporterId);

  if (!open || !transporter) return null;

  const vehicles = data?.items || [];

  const handleOpenAdd = () => {
    setEditingVehicle(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (vehicle) => {
    setEditingVehicle(vehicle);
    setIsFormOpen(true);
  };

  const handleSaveVehicle = async (formData) => {
    try {
      if (editingVehicle) {
        await updateVehicle({
          vehicleId: editingVehicle.id,
          data: formData,
        });
      } else {
        await createVehicle(formData);
      }
      setIsFormOpen(false);
      setEditingVehicle(null);
      refetch();
    } catch (err) {
      console.error('Failed to save vehicle:', err);
      throw err;
    }
  };

  const handleToggleStatus = async (vehicle) => {
    const nextStatus = vehicle.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateVehicle({
        vehicleId: vehicle.id,
        data: { status: nextStatus },
      });
      refetch();
    } catch (err) {
      console.error('Failed to toggle vehicle status:', err);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingVehicle) return;
    try {
      await deleteVehicle(deletingVehicle.id);
      setDeletingVehicle(null);
      refetch();
    } catch (err) {
      console.error('Failed to delete vehicle:', err);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
        {/* Backdrop */}
        <button
          type="button"
          className="absolute inset-0 bg-gray-900/50 backdrop-blur-xs transition-opacity"
          aria-label="Close vehicles master"
          onClick={onClose}
        />

        {/* Modal Window */}
        <div
          role="dialog"
          aria-modal="true"
          className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden flex flex-col max-h-[88vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-linear-to-r from-blue-50/50 to-indigo-50/30">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
                <Truck size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-gray-900">Vehicles Fleet</h2>
                  <Badge variant="primary" size="sm">
                    {transporter.code}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500">
                  Manage registered vehicles for{' '}
                  <span className="font-semibold text-gray-800">{transporter.name}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button size="sm" onClick={handleOpenAdd} className="flex items-center gap-1.5 shadow-xs">
                <Plus size={16} />
                <span>Add Vehicle</span>
              </Button>
              <button
                type="button"
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Search bar & summary */}
          <div className="px-6 py-3 bg-gray-50/70 border-b border-gray-100 flex items-center justify-between gap-4">
            <div className="relative flex-1 max-w-xs">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search vehicle no, driver..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="text-xs font-medium text-gray-500">
              Total: <span className="font-bold text-gray-800">{vehicles.length}</span> vehicle
              {vehicles.length === 1 ? '' : 's'} registered
            </div>
          </div>

          {/* Table Body */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="p-12 text-center text-sm text-gray-500">Loading vehicles...</div>
            ) : vehicles.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-500 mx-auto flex items-center justify-center mb-3">
                  <Truck size={24} />
                </div>
                <h3 className="text-sm font-semibold text-gray-800 mb-1">No vehicles registered yet</h3>
                <p className="text-xs text-gray-500 max-w-sm mx-auto mb-4">
                  Add vehicle registration numbers, drivers, and capacity for {transporter.name} to
                  use during inward/outward dispatch and gate passes.
                </p>
                <Button size="sm" onClick={handleOpenAdd}>
                  <Plus size={15} className="mr-1" />
                  Add First Vehicle
                </Button>
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50/80 text-gray-600 uppercase font-semibold text-[11px] border-b border-gray-200 sticky top-0 z-10">
                  <tr>
                    <th className="px-5 py-3">Vehicle Number</th>
                    <th className="px-4 py-3">Type / Capacity</th>
                    <th className="px-4 py-3">Driver Name</th>
                    <th className="px-4 py-3">Driver Phone</th>
                    <th className="px-4 py-3">RC Number</th>
                    <th className="px-4 py-3 text-center">Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {vehicles.map((v) => (
                    <tr
                      key={v.id}
                      className="hover:bg-blue-50/30 transition-colors group"
                    >
                      <td className="px-5 py-3.5 font-bold text-gray-900 tracking-wider">
                        {v.vehicle_number}
                      </td>
                      <td className="px-4 py-3.5 text-gray-700">
                        <div>{v.vehicle_type || '—'}</div>
                        {v.capacity && (
                          <div className="text-[10px] text-gray-400 font-medium">
                            Cap: {v.capacity}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-gray-700">
                        {v.driver_name ? (
                          <div className="flex items-center gap-1.5">
                            <User size={13} className="text-gray-400 shrink-0" />
                            <span>{v.driver_name}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-gray-700">
                        {v.driver_phone ? (
                          <div className="flex items-center gap-1.5">
                            <Phone size={13} className="text-gray-400 shrink-0" />
                            <span>{v.driver_phone}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-gray-500 font-mono text-[11px]">
                        {v.rc_number || '—'}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleStatus(v)}
                          title="Click to toggle status"
                          className="cursor-pointer"
                        >
                          <StatusBadge status={v.status} />
                        </button>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(v)}
                            className="p-1 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50 transition-colors"
                            title="Edit Vehicle"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeletingVehicle(v)}
                            className="p-1 text-gray-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors"
                            title="Delete Vehicle"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3.5 bg-gray-50/70 border-t border-gray-100 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Manage vehicles registered under {transporter.name}.
            </div>
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>

      {/* Nested Vehicle Add/Edit Form Modal */}
      <VehicleFormModal
        open={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setEditingVehicle(null);
        }}
        onSubmit={handleSaveVehicle}
        initialData={editingVehicle}
        transporterId={transporter.id}
        isLoading={isCreating || isUpdating}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={Boolean(deletingVehicle)}
        title="Delete Vehicle Registration"
        description={`Are you sure you want to remove vehicle "${deletingVehicle?.vehicle_number}" from ${transporter.name}? This action cannot be undone.`}
        confirmLabel="Delete Vehicle"
        variant="danger"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeletingVehicle(null)}
      />
    </>
  );
};

export default TransporterVehiclesModal;
