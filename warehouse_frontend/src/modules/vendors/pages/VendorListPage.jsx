import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useVendors, useUpdateVendor } from '../hooks/use-vendors';
import { useImport, useExport } from '../../../hooks/use-migration';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';
import ImportModal from '../../../components/tables/ImportModal';

const VendorListPage = () => {
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-28' },
    { key: 'name', label: 'Supplier Name', sortable: true },
    { key: 'gstin', label: 'GSTIN' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone' },
    { key: 'company_name', label: 'Company' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'created_at', label: 'Created', type: 'datetime' },
  ];

  const list = useListState({
    defaultSortBy: 'name',
    initialColumns,
  });

  const { data, isLoading, isFetching, error, refetch } = useVendors(list.params);
  const { mutateAsync: updateVendor } = useUpdateVendor();
  const { mutate: doExport } = useExport();
  const { mutate: doImport, isPending: isImporting } = useImport();

  const handleToggleStatus = async (vendor) => {
    const isCurrentlyActive = isEntityActive(vendor);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateVendor({
        id: vendor.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} supplier:`, err);
    }
  };

  const handleExport = () => {
    doExport({ type: 'VENDOR', format: 'excel' });
  };

  const handleImport = ({ file, mapping }) => {
    doImport(
      { type: 'VENDOR', file, mapping },
      {
        onSuccess: () => {
          setIsImportOpen(false);
          refetch();
          alert('Import started successfully!');
        },
        onError: (err) => alert('Import failed: ' + err.message),
      }
    );
  };

  const renderRowActions = (vendor) => {
    const isActive = isEntityActive(vendor);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/suppliers/${vendor.id}`) },
          { type: 'edit', label: 'Edit Supplier', onClick: () => navigate(`/suppliers/${vendor.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(vendor),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(vendor),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', vendor.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <>
      <ListPage
        title="Suppliers"
        description="Manage suppliers, GSTIN details and commercial contacts."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Suppliers' },
        ]}
        createTo="/suppliers/new"
        createLabel="Add Supplier"
        canCreate={true}
        showSupplierFilter={false}
        searchPlaceholder="Search by supplier code, name or GSTIN..."
        searchValue={list.searchInput}
        onSearchChange={list.setSearchInput}
        onRefresh={refetch}
        onExport={handleExport}
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
        actions={renderRowActions}
        rows={data?.items || []}
        isLoading={isLoading}
        isFetching={isFetching}
        error={error}
        onRetry={refetch}
        sorting={{ key: list.sortBy, order: list.sortOrder }}
        onSort={list.handleSort}
        onRowClick={(vendor) => navigate(`/suppliers/${vendor.id}`)}
        emptyTitle="No suppliers found"
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
        title="Suppliers"
        isLoading={isImporting}
        onImport={handleImport}
        fields={[
          { key: 'code', label: 'Code', required: true },
          { key: 'name', label: 'Name', required: true },
          { key: 'legal_name', label: 'Legal Name' },
          { key: 'gstin', label: 'GSTIN' },
          { key: 'billing_address', label: 'Address' },
          { key: 'phone', label: 'Phone' },
          { key: 'contact_person', label: 'Contact Person' },
          { key: 'invoice_workflow', label: 'Invoice Workflow' },
          { key: 'status', label: 'Status' },
        ]}
        sampleUrl="VENDOR"
      />
    </>
  );
};

export default VendorListPage;
