import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useCustomers, useUpdateCustomer } from '../hooks/use-customers';
import { useImport, useExport } from '../../../hooks/use-migration';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';
import ImportModal from '../../../components/tables/ImportModal';

const CustomerListPage = () => {
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Customer Name', sortable: true },
    { key: 'gstin', label: 'GSTIN', widthClass: 'w-40' },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone', widthClass: 'w-32' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useCustomers({
    ...list.params,
    is_buyer: false,
  });
  const { mutateAsync: updateCustomer } = useUpdateCustomer();
  const { mutate: doExport } = useExport();
  const { mutate: doImport, isPending: isImporting } = useImport();

  const handleToggleStatus = async (customer) => {
    const isCurrentlyActive = isEntityActive(customer);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCustomer({
        id: customer.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} customer:`, err);
    }
  };

  const handleExport = () => {
    doExport({ type: 'CUSTOMER', format: 'excel' });
  };

  const handleImport = ({ file, mapping }) => {
    doImport(
      { type: 'CUSTOMER', file, mapping },
      {
        onSuccess: () => {
          setIsImportOpen(false);
          refetch();
          alert('Import started successfully!');
        },
        onError: (err) => alert('Import failed: ' + err.message)
      }
    );
  };

  const renderRowActions = (customer) => {
    const isActive = isEntityActive(customer);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/customers/${customer.id}`) },
          { type: 'edit', label: 'Edit Customer', onClick: () => navigate(`/customers/${customer.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(customer),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(customer),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', customer.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <>
      <ListPage
        title="Customers"
        description="Manage customer master data, billing profiles and commercial terms."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' }, 
          { label: 'Masters' }, 
          { label: 'Customers' }
        ]}
        createTo="/customers/new"
        createLabel="Add Customer"
        canCreate={true}
        searchPlaceholder="Search by customer code, name or GSTIN..."
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
        onRowClick={(customer) => navigate(`/customers/${customer.id}`)}
        emptyTitle="No customers found"
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
        title="Customers"
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

export default CustomerListPage;
