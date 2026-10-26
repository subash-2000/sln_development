import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { ringsApi } from '../api/rings.api';
import { useRingsDocuments } from '../hooks/use-rings';

const RingsDispatchPage = () => {
  const navigate = useNavigate();
  const initialColumns = [
    { key: 'document_number', label: 'Outward No' },
    { key: 'workflow', label: 'Workflow' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'customer_name', label: 'Buyer' },
    { key: 'sln_challan_number', label: 'SLN Challan' },
    { key: 'supplier_customer_invoice_number', label: 'Supplier Invoice' },
    { key: 'gross_weight', label: 'Gross Wt' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const list = useListState({ defaultSortOrder: 'desc', initialColumns });
  const { data, isLoading, isFetching, error, refetch } = useRingsDocuments({
    ...list.params,
    document_type: 'OUTWARD',
  });

  return (
    <ListPage
      title="Dispatch / Challan"
      description="Job Work: SLN delivery challan only (no GST). Direct Invoice: supplier tax invoice travels with the material."
      breadcrumbs={[{ label: 'Dashboard', to: '/dashboard' }, { label: 'Operations' }, { label: 'Dispatch / Challan' }]}
      canCreate={false}
      onExport={() => ringsApi.downloadChallansXlsx().catch((e) => window.alert(e.message))}
      searchPlaceholder="Search outward or challan..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={(row) => (
        <RowActions
          actions={[
            { type: 'view', label: 'View', onClick: () => navigate(`/rings/dispatch/${row.id}`) },
            {
              type: 'custom',
              label: 'Download SLN challan Excel',
              onClick: () => ringsApi.downloadChallanXlsx(row.id).catch((e) => window.alert(e.message)),
              hidden: row.workflow !== 'JOB_WORK',
            },
            {
              type: 'custom',
              label: 'Download SLN challan PDF',
              onClick: () => ringsApi.downloadChallanPdf(row.id).catch((e) => window.alert(e.message)),
              hidden: row.workflow !== 'JOB_WORK',
            },
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
          ]}
        />
      )}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      onRowClick={(row) => navigate(`/rings/dispatch/${row.id}`)}
      emptyTitle="No dispatches yet"
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

export default RingsDispatchPage;
