import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useBins } from '../hooks/use-bins';
import { useUpdateLocation } from '../../locations/hooks/use-locations';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';

const BinListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Bin Name', sortable: true },
    { key: 'path', label: 'Hierarchy' },
    { key: 'bin', label: 'Bin', widthClass: 'w-24' },
    { key: 'shelf', label: 'Shelf', widthClass: 'w-24' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'code',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useBins(list.params);
  const { mutateAsync: updateLocation } = useUpdateLocation();

  const handleToggleStatus = async (bin) => {
    const isCurrentlyActive = isEntityActive(bin);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateLocation({
        id: bin.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} bin:`, err);
    }
  };

  const renderRowActions = (bin) => {
    const isActive = isEntityActive(bin);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/locations/${bin.id}/edit`) },
          { type: 'edit', label: 'Edit Bin', onClick: () => navigate(`/locations/${bin.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(bin),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(bin),
            hidden: isActive,
          },
        ]}
      />
    );
  };

  return (
    <ListPage
      title="Bins"
      description="Manage warehouse bin storage locations and layout hierarchy."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Warehouse' }, 
        { label: 'Bins' }
      ]}
      createTo="/bins/new"
      createLabel="Add Bin"
      canCreate={true}
      searchPlaceholder="Search bins by code, name or path..."
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
      onRowClick={(bin) => navigate(`/locations/${bin.id}/edit`)}
      emptyTitle="No bins found"
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

export default BinListPage;
