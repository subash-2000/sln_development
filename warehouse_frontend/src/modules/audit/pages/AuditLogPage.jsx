import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useListState } from '../../../hooks/use-list-state';
import { auditApi } from '../api/audit.api';
import ListPage from '../../../components/tables/ListPage';

const AuditLogPage = () => {
  const initialColumns = [
    { key: 'timestamp', label: 'Timestamp', type: 'datetime', sortable: true, widthClass: 'w-48' },
    { key: 'user_name', label: 'User', widthClass: 'w-40' },
    { key: 'module', label: 'Module', widthClass: 'w-32' },
    { key: 'entity_name', label: 'Entity', widthClass: 'w-32' },
    { key: 'action', label: 'Action', widthClass: 'w-32' },
    { key: 'entity_id', label: 'Reference ID', widthClass: 'w-40' },
    { key: 'request_id', label: 'Request ID', widthClass: 'w-48' },
  ];

  const list = useListState({ 
    defaultSortBy: 'timestamp', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['audit-logs', list.params],
    queryFn: () => auditApi.list(list.params),
    placeholderData: (previous) => previous,
  });

  const handleExport = () => {
    console.log('Exporting audit logs...');
  };

  return (
    <ListPage
      title="Audit Trail"
      description="Track system mutations, status changes and administrative actions across all modules."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Administration' }, 
        { label: 'Audit Logs' }
      ]}
      canCreate={false}
      searchPlaceholder="Search by module, entity or user..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      onExport={handleExport}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      emptyTitle="No audit logs found"
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

export default AuditLogPage;
