import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Truck, Building2, Plus, Star, Phone, User, Edit2, Trash2 } from 'lucide-react';
import { useListState } from '../../../hooks/use-list-state';
import {
  useTransporters,
  useUpdateTransporter,
  useAllVehicles,
  useCreateVehicle,
  useUpdateVehicle,
  useDeleteVehicle,
} from '../hooks/use-transporters';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import Button from '../../../components/ui/Button';
import TransporterVehiclesModal from '../components/TransporterVehiclesModal';
import VehicleFormModal from '../components/VehicleFormModal';
import ConfirmDialog from '../../../components/modals/ConfirmDialog';
import { isEntityActive } from '../../../constants/status';

const TransporterListPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('transporters'); // 'transporters' | 'vehicles'

  // Transporter list state
  const transporterColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-24' },
    { key: 'name', label: 'Transporter Name', sortable: true },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-36' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone', widthClass: 'w-32' },
    { key: 'vehicles_fleet', label: 'Fleet / Vehicles', widthClass: 'w-40', align: 'center' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const transporterList = useListState({ defaultSortBy: 'name', initialColumns: transporterColumns });
  const {
    data: transportersData,
    isLoading: isLoadingTransporters,
    isFetching: isFetchingTransporters,
    error: transportersError,
    refetch: refetchTransporters,
  } = useTransporters(transporterList.params);
  const { mutateAsync: updateTransporter } = useUpdateTransporter();

  // All linked vehicles state
  const vehicleColumns = [
    { key: 'vehicle_number', label: 'Vehicle No.', sortable: true, widthClass: 'w-40' },
    { key: 'transporter_name', label: 'Linked Transporter', sortable: true },
    { key: 'vehicle_type', label: 'Type' },
    { key: 'capacity', label: 'Capacity' },
    { key: 'driver_name', label: 'Driver' },
    { key: 'driver_phone', label: 'Phone' },
    { key: 'rc_number', label: 'RC No.' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const vehicleList = useListState({ defaultSortBy: 'vehicle_number', initialColumns: vehicleColumns });
  const {
    data: vehiclesData,
    isLoading: isLoadingVehicles,
    isFetching: isFetchingVehicles,
    error: vehiclesError,
    refetch: refetchVehicles,
  } = useAllVehicles(vehicleList.params);

  // Modals state
  const [vehiclesModalTransporter, setVehiclesModalTransporter] = useState(null);
  const [isAddVehicleOpen, setIsAddVehicleOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [deletingVehicle, setDeletingVehicle] = useState(null);

  const { mutateAsync: createVehicle, isPending: isCreatingVehicle } = useCreateVehicle();
  const { mutateAsync: updateVehicle, isPending: isUpdatingVehicle } = useUpdateVehicle();
  const { mutateAsync: deleteVehicle, isPending: isDeletingVehicle } = useDeleteVehicle();

  const handleToggleTransporterStatus = async (row) => {
    const active = isEntityActive(row);
    await updateTransporter({
      id: row.id,
      data: { status: active ? 'INACTIVE' : 'ACTIVE' },
    });
    refetchTransporters();
  };

  const handleSaveVehicle = async (formData) => {
    try {
      if (editingVehicle) {
        await updateVehicle({
          vehicleId: editingVehicle.id,
          transporterId: editingVehicle.transporter_id,
          data: formData,
        });
      } else {
        await createVehicle(formData);
      }
      setIsAddVehicleOpen(false);
      setEditingVehicle(null);
      refetchTransporters();
      refetchVehicles();
    } catch (err) {
      console.error('Failed to save vehicle:', err);
      throw err;
    }
  };

  const handleToggleVehicleStatus = async (row) => {
    const active = isEntityActive(row);
    await updateVehicle({
      vehicleId: row.id,
      transporterId: row.transporter_id,
      data: { status: active ? 'INACTIVE' : 'ACTIVE' },
    });
    refetchVehicles();
    refetchTransporters();
  };

  const handleConfirmDeleteVehicle = async () => {
    if (!deletingVehicle) return;
    await deleteVehicle({
      vehicleId: deletingVehicle.id,
      transporterId: deletingVehicle.transporter_id,
    });
    setDeletingVehicle(null);
    refetchVehicles();
    refetchTransporters();
  };

  const renderTransporterActions = (row) => (
    <RowActions
      actions={[
        {
          type: 'custom',
          label: 'Manage Vehicles',
          icon: Truck,
          onClick: () => setVehiclesModalTransporter(row),
        },
        { type: 'view', label: 'View / Edit', onClick: () => navigate(`/transport/${row.id}`) },
        {
          type: 'toggle',
          label: isEntityActive(row) ? 'Deactivate' : 'Activate',
          onClick: () => handleToggleTransporterStatus(row),
        },
      ]}
    />
  );

  const renderVehicleActions = (row) => (
    <RowActions
      actions={[
        {
          type: 'view',
          label: 'Edit Vehicle',
          onClick: () => {
            setEditingVehicle(row);
            setIsAddVehicleOpen(true);
          },
        },
        {
          type: 'toggle',
          label: isEntityActive(row) ? 'Deactivate' : 'Activate',
          onClick: () => handleToggleVehicleStatus(row),
        },
        {
          type: 'delete',
          label: 'Delete',
          onClick: () => setDeletingVehicle(row),
        },
      ]}
    />
  );

  // Formatted rows for Transporters
  const formattedTransporters = (transportersData?.items || []).map((row) => {
    const count = row.vehicles_count ?? (row.vehicles ? row.vehicles.length : 0);

    return {
      ...row,
      vehicles_fleet: (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setVehiclesModalTransporter(row);
          }}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 hover:text-blue-800 border border-blue-200 transition-colors shadow-2xs"
          title={`Click to view/add vehicles for ${row.name}`}
        >
          <Truck size={13} />
          <span>
            {count} {count === 1 ? 'Vehicle' : 'Vehicles'}
          </span>
        </button>
      ),
    };
  });

  // Formatted rows for Vehicles
  const formattedVehicles = (vehiclesData?.items || []).map((row) => ({
    ...row,
    transporter_name: (
      <div className="text-xs">
        <span className="font-semibold text-gray-900">{row.transporter_name || '—'}</span>
        {row.transporter_code && (
          <span className="ml-1.5 text-[11px] text-gray-500 font-mono">({row.transporter_code})</span>
        )}
      </div>
    ),
  }));

  const totalTransporters =
    transportersData?.pagination?.total || (transportersData?.items || []).length;
  const totalVehicles =
    vehiclesData?.pagination?.total || (vehiclesData?.items || []).length;

  return (
    <div className="space-y-4">
      {/* Unified Transport Master Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-gray-200 pb-3">
        {/* Sub-tabs within Transport Master */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('transporters')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'transporters'
                ? 'text-blue-600 bg-blue-50 border border-blue-200 font-semibold shadow-2xs'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Building2 size={16} />
            <span>Transporters</span>
            <span
              className={`ml-1 text-xs px-2 py-0.5 rounded-full font-bold ${
                activeTab === 'transporters'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              {totalTransporters}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('vehicles')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'vehicles'
                ? 'text-blue-600 bg-blue-50 border border-blue-200 font-semibold shadow-2xs'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Truck size={16} />
            <span>All Linked Vehicles</span>
            <span
              className={`ml-1 text-xs px-2 py-0.5 rounded-full font-bold ${
                activeTab === 'vehicles'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              {totalVehicles}
            </span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setEditingVehicle(null);
              setIsAddVehicleOpen(true);
            }}
            className="flex items-center gap-1.5"
          >
            <Truck size={15} />
            <span>+ Add Vehicle</span>
          </Button>

          <Button
            size="sm"
            onClick={() => navigate('/transport/new')}
            className="flex items-center gap-1.5 shadow-xs"
          >
            <Plus size={16} />
            <span>New Transporter</span>
          </Button>
        </div>
      </div>

      {/* Tab 1: Transporters List */}
      {activeTab === 'transporters' ? (
        <ListPage
          title="Transport Master"
          description="Manage transporters and their inter-linked vehicle fleets."
          breadcrumbs={[
            { label: 'Dashboard', to: '/dashboard' },
            { label: 'Masters' },
            { label: 'Transport' },
          ]}
          searchPlaceholder="Search by code, name, GSTIN or phone..."
          searchValue={transporterList.searchInput}
          onSearchChange={transporterList.setSearchInput}
          onRefresh={refetchTransporters}
          columns={transporterList.columns}
          onToggleColumn={transporterList.toggleColumn}
          actions={renderTransporterActions}
          rows={formattedTransporters}
          isLoading={isLoadingTransporters}
          isFetching={isFetchingTransporters}
          error={transportersError}
          onRetry={refetchTransporters}
          sorting={{ key: transporterList.sortBy, order: transporterList.sortOrder }}
          onSort={transporterList.handleSort}
          onRowClick={(row) => navigate(`/transport/${row.id}`)}
          emptyTitle="No transporters found"
          pagination={{
            currentPage: transporterList.page,
            pageSize: transporterList.pageSize,
            totalRecords: transportersData?.pagination?.total || 0,
            onPageChange: transporterList.setPage,
            onPageSizeChange: transporterList.setPageSize,
          }}
        />
      ) : (
        /* Tab 2: All Linked Vehicles */
        <ListPage
          title="Transport Master — Registered Vehicles"
          description="All vehicles inter-linked with their respective transporters."
          breadcrumbs={[
            { label: 'Dashboard', to: '/dashboard' },
            { label: 'Masters' },
            { label: 'Transport' },
            { label: 'Vehicles' },
          ]}
          searchPlaceholder="Search by vehicle no, driver name, phone, RC..."
          searchValue={vehicleList.searchInput}
          onSearchChange={vehicleList.setSearchInput}
          onRefresh={refetchVehicles}
          columns={vehicleList.columns}
          onToggleColumn={vehicleList.toggleColumn}
          actions={renderVehicleActions}
          rows={formattedVehicles}
          isLoading={isLoadingVehicles}
          isFetching={isFetchingVehicles}
          error={vehiclesError}
          onRetry={refetchVehicles}
          sorting={{ key: vehicleList.sortBy, order: vehicleList.sortOrder }}
          onSort={vehicleList.handleSort}
          onRowClick={(row) => {
            setEditingVehicle(row);
            setIsAddVehicleOpen(true);
          }}
          emptyTitle="No vehicles registered yet"
          pagination={{
            currentPage: vehicleList.page,
            pageSize: vehicleList.pageSize,
            totalRecords: vehiclesData?.pagination?.total || 0,
            onPageChange: vehicleList.setPage,
            onPageSizeChange: vehicleList.setPageSize,
          }}
        />
      )}

      {/* Quick Manage Vehicles for Specific Transporter Modal */}
      <TransporterVehiclesModal
        open={Boolean(vehiclesModalTransporter)}
        onClose={() => {
          setVehiclesModalTransporter(null);
          refetchTransporters();
          refetchVehicles();
        }}
        transporter={vehiclesModalTransporter}
      />

      {/* Unified Add/Edit Vehicle Modal with Transporter Selector */}
      <VehicleFormModal
        open={isAddVehicleOpen}
        onClose={() => {
          setIsAddVehicleOpen(false);
          setEditingVehicle(null);
        }}
        onSubmit={handleSaveVehicle}
        initialData={editingVehicle}
        transporterId={editingVehicle?.transporter_id}
        isLoading={isCreatingVehicle || isUpdatingVehicle}
      />

      {/* Delete Vehicle Confirmation */}
      <ConfirmDialog
        open={Boolean(deletingVehicle)}
        title="Delete Vehicle Registration"
        description={`Are you sure you want to delete vehicle "${deletingVehicle?.vehicle_number}" from ${deletingVehicle?.transporter_name || 'transporter'}?`}
        confirmLabel="Delete Vehicle"
        variant="danger"
        isLoading={isDeletingVehicle}
        onConfirm={handleConfirmDeleteVehicle}
        onClose={() => setDeletingVehicle(null)}
      />
    </div>
  );
};

export default TransporterListPage;
