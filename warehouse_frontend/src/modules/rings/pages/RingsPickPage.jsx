import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { ringsApi } from '../api/rings.api';
import { useDispatchRingsPick, useRingsDocuments } from '../hooks/use-rings';

const RingsPickPage = () => {
  const navigate = useNavigate();
  const { mutateAsync: dispatchPick, isPending } = useDispatchRingsPick();
  const initialColumns = [
    { key: 'document_number', label: 'Pick No', sortable: true },
    { key: 'workflow', label: 'Workflow' },
    {
      key: 'vendor_name',
      label: 'Supplier',
      render: (val, row) => {
        const uniqueSuppliers = Array.from(new Set((row.lines || []).map((l) => l.vendor_name).filter(Boolean)));
        if (uniqueSuppliers.length > 1) {
          return `Multiple (${uniqueSuppliers.length} suppliers)`;
        }
        return val || uniqueSuppliers[0] || '—';
      },
    },
    { key: 'customer_name', label: 'Buyer' },
    { key: 'supplier_document_number', label: 'Source Doc' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const list = useListState({ defaultSortOrder: 'desc', initialColumns });
  const { data, isLoading, isFetching, error, refetch } = useRingsDocuments({
    ...list.params,
    document_type: 'PICK',
  });

  const handleDispatch = async (row) => {
    let invoice = '';
    if (row.workflow === 'DIRECT_INVOICE') {
      invoice = window.prompt('Supplier customer invoice number (required; SLN will not generate a tax invoice)') || '';
      if (!invoice) return;
    }
    try {
      await dispatchPick({
        id: row.id,
        data: { supplier_customer_invoice_number: invoice || undefined },
      });
      refetch();
    } catch (err) {
      window.alert(err.response?.data?.message || err.message);
    }
  };

  return (
    <ListPage
      title="Picking List"
      description="Download Excel or PDF from the toolbar or a row."
      breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Operations' }, { label: 'Picking List' }]}
      createTo="/rings/picks/new"
      createLabel="New Pick Slip"
      canCreate
      onExport={() => ringsApi.downloadPicksXlsx().catch((e) => window.alert(e.message))}
      toolbarExtra={(
        <button
          type="button"
          className="h-9 px-3 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50"
          onClick={() => ringsApi.downloadPicksPdf().catch((e) => window.alert(e.message))}
        >
          PDF
        </button>
      )}
      searchPlaceholder="Search pick slips..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={(row) => (
        <RowActions
          actions={[
            { type: 'view', label: 'View', onClick: () => navigate(`/rings/picks/${row.id}`) },
            {
              type: 'custom',
              label: 'Download pick slip Excel',
              onClick: () => ringsApi.downloadPickXlsx(row.id).catch((e) => window.alert(e.message)),
            },
            {
              type: 'custom',
              label: 'Download pick slip PDF',
              onClick: () => ringsApi.downloadPickPdf(row.id).catch((e) => window.alert(e.message)),
            },
            {
              type: 'custom',
              label: 'Download SLN challan Excel',
              onClick: () => ringsApi.downloadChallanXlsx(row.id).catch((e) => window.alert(e.message)),
              hidden: row.workflow !== 'JOB_WORK' || row.status !== 'POSTED',
            },
            {
              type: 'custom',
              label: 'Download SLN challan PDF',
              onClick: () => ringsApi.downloadChallanPdf(row.id).catch((e) => window.alert(e.message)),
              hidden: row.workflow !== 'JOB_WORK' || row.status !== 'POSTED',
            },
            {
              type: 'custom',
              label: isPending ? 'Posting…' : 'Dispatch',
              onClick: () => handleDispatch(row),
              hidden: row.status !== 'DRAFT',
            },
          ]}
        />
      )}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      emptyTitle="No pick slips"
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

export default RingsPickPage;
