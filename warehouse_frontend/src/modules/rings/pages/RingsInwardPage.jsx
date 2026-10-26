import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { useRingsDocuments } from '../hooks/use-rings';

const RingsInwardPage = () => {
  const navigate = useNavigate();
  const initialColumns = [
    { key: 'document_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'created_at', label: 'Date', type: 'datetime', sortable: true },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'supplier_document_number', label: 'Source Doc', widthClass: 'w-40' },
    { key: 'transporter_name', label: 'Transporter' },
    { key: 'packing_weight', label: 'Packing Wt' },
    { key: 'gross_weight', label: 'Gross Wt' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const list = useListState({ defaultSortBy: 'created_at', defaultSortOrder: 'desc', initialColumns });
  const { data, isLoading, isFetching, error, refetch } = useRingsDocuments({
    ...list.params,
    document_type: 'INWARD',
  });

  return (
    <ListPage
      title="Inward Transactions"
      description="Manage material receipts and inbound stock movements."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Operations' },
        { label: 'Inward' },
      ]}
      createTo="/rings/inward/new"
      createLabel="New Inward"
      canCreate
      searchPlaceholder="Search by transaction number or reference..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'POSTED', label: 'Completed' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={(row) => (
        <RowActions
          actions={[
            { type: 'view', label: 'View Details', onClick: () => navigate(`/rings/inward/${row.id}`) },
          ]}
        />
      )}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(row) => navigate(`/rings/inward/${row.id}`)}
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

export default RingsInwardPage;
