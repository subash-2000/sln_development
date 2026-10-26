import React from 'react';
import { useListState } from '../../../hooks/use-list-state';
import { useQuery } from '@tanstack/react-query';
import { rolesApi } from '../api/roles.api';
import ListPage from '../../../components/tables/ListPage';

const PermissionListPage = () => {
  const initialColumns = [
    { key: 'code', label: 'Permission Code', sortable: true, widthClass: 'w-64' },
    { key: 'module', label: 'Module', sortable: true, widthClass: 'w-40' },
    { key: 'description', label: 'Description' },
    { key: 'is_active', label: 'Status', type: 'status', render: (val) => val ? 'ACTIVE' : 'INACTIVE' },
  ];

  const list = useListState({
    initialColumns
  });
  
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => rolesApi.permissions(),
    placeholderData: (previous) => previous,
  });

  const search = (list.searchInput || '').toLowerCase();
  const rows = (data?.items || []).filter((row) => {
    if (!search) return true;
    return [row.code, row.module, row.description].some((value) =>
      String(value || '').toLowerCase().includes(search)
    );
  });

  return (
    <ListPage
      title="Permissions"
      description="System-defined permissions available for role assignment."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Administration' }, 
        { label: 'Permissions' }
      ]}
      canCreate={false}
      showSupplierFilter={false}
      searchPlaceholder="Search by permission code, module or description..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={rows}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      emptyTitle="No permissions found"
      pagination={{
        currentPage: 1,
        pageSize: rows.length || 25,
        totalRecords: rows.length,
        onPageChange: () => {},
        onPageSizeChange: () => {},
      }}
    />
  );
};

export default PermissionListPage;
