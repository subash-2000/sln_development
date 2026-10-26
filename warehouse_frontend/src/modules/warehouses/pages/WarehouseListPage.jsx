import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useWarehouses, useUpdateWarehouse } from '../hooks/use-warehouses';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const WarehouseListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Warehouse Name', sortable: true },
    { key: 'warehouse_type', label: 'Type', widthClass: 'w-28' },
    { key: 'city', label: 'City', widthClass: 'w-32' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useWarehouses(list.params);
  const { mutateAsync: updateWarehouse } = useUpdateWarehouse();

  const handleToggleStatus = async (warehouse) => {
    const isCurrentlyActive = isEntityActive(warehouse);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateWarehouse({
        id: warehouse.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} warehouse:`, err);
    }
  };

  const renderRowActions = (warehouse) => {
    const isActive = isEntityActive(warehouse);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/warehouses/${warehouse.id}`) },
          { type: 'edit', label: 'Edit Warehouse', onClick: () => navigate(`/warehouses/${warehouse.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(warehouse),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(warehouse),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', warehouse.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Warehouses"
      description="Manage warehouse sites, capacity and operational status."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Warehouse' }, 
        { label: 'Warehouses' }
      ]}
      createTo="/warehouses/new"
      createLabel="Add Warehouse"
      canCreate={true}
      searchPlaceholder="Search by warehouse code or name..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'ACTIVE', label: 'Active' },
        { value: 'INACTIVE', label: 'Inactive' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={renderRowActions}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(warehouse) => navigate(`/warehouses/${warehouse.id}`)}
      emptyTitle="No warehouses found"
      pagination={{
        currentPage: list.page,
        pageSize: list.pageSize,
        totalRecords: data?.pagination?.total || 0,
        onPageChange: list.setPage,
        onPageSizeChange: list.setPageSize,
      }}
    />
  );
};

export default WarehouseListPage;
