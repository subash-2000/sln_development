import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { logisticsApi } from '../api/logistics.api';
import { useListState } from '../../../hooks/use-list-state';
import { useLogisticsInward } from '../hooks/use-logistics';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const LogisticsInwardPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'transaction_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'created_at', label: 'Date', type: 'datetime', sortable: true },
    { key: 'partner_vendor_name', label: 'Supplier' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'reference_document_number', label: 'Source Doc', widthClass: 'w-40' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'created_at', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useLogisticsInward(list.params);

  const downloadPdf = useCallback(async (inward) => {
    try {
      await logisticsApi.inward.downloadInvoicePdf(inward.id);
    } catch (e) {
      window.alert(e?.message || 'Failed to download invoice PDF');
    }
  }, []);

  const renderRowActions = (inward) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/logistics/inward/${inward.id}`) },
        {
          type: 'custom',
          label: 'Download invoice PDF',
          onClick: () => downloadPdf(inward),
          hidden: inward.status !== 'COMPLETED',
        },
        { type: 'edit', label: 'Edit Inward', onClick: () => navigate(`/logistics/inward/${inward.id}/edit`), hidden: inward.status !== 'DRAFT' },
        { type: 'delete', label: 'Cancel', onClick: () => console.log('Cancel', inward.id), variant: 'danger', hidden: ['COMPLETED', 'CANCELLED'].includes(inward.status) },
      ]}
    />
  );

  return (
    <ListPage
      title="Inward Transactions"
      description="Manage material receipts and inbound stock movements."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Logistics' }, 
        { label: 'Inward' }
      ]}
      createTo="/logistics/inward/new"
      createLabel="New Inward"
      canCreate={true}
      searchPlaceholder="Search by transaction number or reference..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'COMPLETED', label: 'Completed' },
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
      onRowClick={(inward) => navigate(`/logistics/inward/${inward.id}`)}
      emptyTitle="No inward transactions found"
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

export default LogisticsInwardPage;
