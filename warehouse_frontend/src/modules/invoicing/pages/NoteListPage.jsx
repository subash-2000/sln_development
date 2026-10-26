import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useQuery } from '@tanstack/react-query';
import { invoicingApi } from '../api/invoicing.api';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';

const NoteListPage = () => {
  const navigate = useNavigate();

  const initialColumns = [
    { key: 'invoice_number', label: 'Reference', sortable: true, widthClass: 'w-40' },
    { key: 'invoice_date', label: 'Date', type: 'date', sortable: true },
    { key: 'customer_name', label: 'Customer' },
    { key: 'total_amount', label: 'Total Value', type: 'currency' },
    { key: 'balance_amount', label: 'Balance', type: 'currency' },
    { key: 'status', label: 'Status', type: 'status' },
  ];

  const list = useListState({ 
    defaultSortBy: 'invoice_date', 
    defaultSortOrder: 'desc',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['invoice-notes', list.params],
    queryFn: () => invoicingApi.list(list.params),
    placeholderData: (previous) => previous,
  });

  const renderRowActions = (note) => (
    <RowActions
      actions={[
        { type: 'view', label: 'View Details', onClick: () => navigate(`/invoicing/notes/${note.id}`) },
        { type: 'edit', label: 'Edit Note', onClick: () => navigate(`/invoicing/notes/${note.id}/edit`), hidden: note.status !== 'DRAFT' },
        { type: 'delete', label: 'Cancel Note', onClick: () => console.log('Cancel', note.id), variant: 'danger', hidden: note.status === 'CANCELLED' },
      ]}
    />
  );

  return (
    <ListPage
      title="Credit / Debit Notes"
      description="Manage customer credit and debit notes for invoice adjustments and returns."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Invoicing' }, 
        { label: 'Notes' }
      ]}
      createTo="/invoicing/notes/new"
      createLabel="New Note"
      canCreate={true}
      searchPlaceholder="Search by note number or customer..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'DRAFT', label: 'Draft' },
        { value: 'POSTED', label: 'Posted' },
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
      onRowClick={(note) => navigate(`/invoicing/notes/${note.id}`)}
      emptyTitle="No notes found"
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

export default NoteListPage;
