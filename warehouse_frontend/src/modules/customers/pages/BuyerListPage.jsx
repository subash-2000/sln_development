import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useCustomers, useUpdateCustomer } from '../hooks/use-customers';
import { useImport } from '../../../hooks/use-migration';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import ImportModal from '../../../components/tables/ImportModal';
import { isEntityActive } from '../../../constants/status';

const BuyerListPage = () => {
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);
  const { mutate: doImport, isPending: isImporting } = useImport();
  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Buyer Name', sortable: true },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-40' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
  ];
  const list = useListState({ defaultSortBy: 'name', initialColumns });
  const { data, isLoading, isFetching, error, refetch } = useCustomers({
    ...list.params,
    is_buyer: true,
  });
  const { mutateAsync: updateCustomer } = useUpdateCustomer();

  const handleToggleStatus = async (buyer) => {
    const isCurrentlyActive = isEntityActive(buyer);
    try {
      await updateCustomer({
        id: buyer.id,
        data: { status: isCurrentlyActive ? 'INACTIVE' : 'ACTIVE', is_buyer: true },
      });
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleImport = ({ file, mapping }) => {
    doImport(
      { type: 'CUSTOMER', file, mapping },
      {
        onSuccess: () => {
          setIsImportOpen(false);
          refetch();
        },
        onError: (err) => alert('Import failed: ' + err.message),
      }
    );
  };

  return (
    <>
    <ListPage
      title="Buyers"
      description="Buyer master used on pick, dispatch and sales."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Masters' },
        { label: 'Buyers' },
      ]}
      createTo="/buyers/new"
      createLabel="Add Buyer"
      canCreate
      searchPlaceholder="Search by buyer code, name or GSTIN..."
      searchValue={list.searchInput}
      onSearchChange={list.setSearchInput}
      onRefresh={refetch}
      onImport={() => setIsImportOpen(true)}
      quickFilters={[
        { value: 'ALL', label: 'All' },
        { value: 'ACTIVE', label: 'Active' },
        { value: 'INACTIVE', label: 'Inactive' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      actions={(buyer) => {
        const isActive = isEntityActive(buyer);
        return (
          <RowActions
            actions={[
              { type: 'edit', label: 'Edit Buyer', onClick: () => navigate(`/buyers/${buyer.id}/edit`) },
              {
                type: 'deactivate',
                label: 'Deactivate',
                onClick: () => handleToggleStatus(buyer),
                hidden: !isActive,
              },
              {
                type: 'activate',
                label: 'Activate',
                onClick: () => handleToggleStatus(buyer),
                hidden: isActive,
              },
            ]}
          />
        );
      }}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      onRowClick={(buyer) => navigate(`/buyers/${buyer.id}/edit`)}
      emptyTitle="No buyers found"
      pagination={{
        currentPage: list.page,
        pageSize: list.pageSize,
        totalRecords: data?.pagination?.total || 0,
        onPageChange: list.setPage,
        onPageSizeChange: list.setPageSize,
      }}
    />
    <ImportModal
      isOpen={isImportOpen}
      onClose={() => setIsImportOpen(false)}
      title="Buyers"
      isLoading={isImporting}
      onImport={handleImport}
      fields={[
        { key: 'code', label: 'Code', required: true },
        { key: 'name', label: 'Name', required: true },
        { key: 'gstin', label: 'GSTIN' },
        { key: 'billing_address', label: 'Address' },
        { key: 'contact_person', label: 'Contact Person' },
        { key: 'phone', label: 'Phone' },
        { key: 'is_buyer', label: 'Is Buyer' },
        { key: 'status', label: 'Status' },
      ]}
      sampleUrl="CUSTOMER"
    />
    </>
  );
};

export default BuyerListPage;
