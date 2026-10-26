import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useJobWorkDCS } from '../hooks/use-job-work';
import ListPage from '../../../components/tables/ListPage';

const JobWorkDCSPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'job_work_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'product_name', label: 'Product' },
    { key: 'issue_date', label: 'Issue Date', type: 'date', sortable: true },
    { key: 'consumption_qty', label: 'Consumption', type: 'quantity', widthClass: 'w-32' },
    { key: 'wastage_qty', label: 'Wastage', type: 'quantity', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'job_work_number',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useJobWorkDCS(list.params);

  const handleExport = () => {
    window.print();
  };

  return (
    <ListPage
      title="Job Work DCS"
      description="Daily Consumption Status (DCS) for tracking material usage and wastage at supplier sites."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Job Work' }, 
        { label: 'DCS' }
      ]}
      canCreate={false}
      searchPlaceholder="Search by job work number or supplier..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      onExport={handleExport}
      quickFilters={[
        { value: 'ALL', label: 'All DCS' },
        { value: 'IN_PROCESS', label: 'In Process' },
        { value: 'COMPLETED', label: 'Completed' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(order) => navigate(`/job-work/register/${order.id}`)}
      emptyTitle="No DCS records found"
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

export default JobWorkDCSPage;
