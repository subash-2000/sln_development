import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useRacks } from '../hooks/use-racks';
import { useUpdateLocation } from '../../locations/hooks/use-locations';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const RackListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Rack Name', sortable: true },
    { key: 'path', label: 'Hierarchy' },
    { key: 'aisle', label: 'Aisle', widthClass: 'w-24' },
    { key: 'rack', label: 'Rack', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'code',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useRacks(list.params);
  const { mutateAsync: updateLocation } = useUpdateLocation();

  const handleToggleStatus = async (rack) => {
    const isCurrentlyActive = isEntityActive(rack);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateLocation({
        id: rack.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} rack:`, err);
    }
  };

  const renderRowActions = (rack) => {
    const isActive = isEntityActive(rack);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/locations/${rack.id}/edit`) },
          { type: 'edit', label: 'Edit Rack', onClick: () => navigate(`/locations/${rack.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(rack),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(rack),
            hidden: isActive,
          },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Racks"
      description="Manage warehouse rack storage systems and spatial layout."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Warehouse' }, 
        { label: 'Racks' }
      ]}
      createTo="/racks/new"
      createLabel="Add Rack"
      canCreate={true}
      searchPlaceholder="Search racks by code, name or path..."
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
      onRowClick={(rack) => navigate(`/locations/${rack.id}/edit`)}
      emptyTitle="No racks found"
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

export default RackListPage;
