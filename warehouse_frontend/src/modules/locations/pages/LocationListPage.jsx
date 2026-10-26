import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useLocations, useUpdateLocation } from '../hooks/use-locations';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const LocationListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Location Name', sortable: true },
    { key: 'path', label: 'Hierarchy' },
    { key: 'storage_type', label: 'Storage Type', widthClass: 'w-28' },
    { key: 'location_type', label: 'Type', widthClass: 'w-24' },
    { key: 'zone', label: 'Zone', widthClass: 'w-24' },
    { key: 'is_blocked', label: 'Blocked', type: 'boolean', widthClass: 'w-20' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'code',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useLocations(list.params);
  const { mutateAsync: updateLocation } = useUpdateLocation();

  const handleToggleStatus = async (location) => {
    const isCurrentlyActive = isEntityActive(location);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateLocation({
        id: location.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} location:`, err);
    }
  };

  const renderRowActions = (location) => {
    const isActive = isEntityActive(location);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/locations/${location.id}`) },
          { type: 'edit', label: 'Edit Location', onClick: () => navigate(`/locations/${location.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(location),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(location),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', location.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Locations"
      description="Manage warehouse locations, bins, racks and storage hierarchy."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Warehouse' }, 
        { label: 'Locations' }
      ]}
      createTo="/locations/new"
      createLabel="Add Location"
      canCreate={true}
      searchPlaceholder="Search by location code, name or path..."
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
      onRowClick={(location) => navigate(`/locations/${location.id}/edit`)}
      emptyTitle="No locations found"
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

export default LocationListPage;
