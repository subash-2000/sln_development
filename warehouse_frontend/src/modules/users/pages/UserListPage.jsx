import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useUsers, useUpdateUser } from '../hooks/use-users';
import { useImport, useExport } from '../../../hooks/use-migration';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';
import ImportModal from '../../../components/tables/ImportModal';

const UserListPage = () => {
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);

  const initialColumns = [
    { key: 'username', label: 'Username', sortable: true },
    { key: 'full_name', label: 'Full Name', sortable: true },
    { key: 'email', label: 'Email' },
    { key: 'roles', label: 'Roles', render: (val) => (Array.isArray(val) ? val.join(', ') : val || '-') },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'last_login', label: 'Last Login', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'username',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useUsers(list.params);
  const { mutateAsync: updateUser } = useUpdateUser();
  const { mutate: doExport } = useExport();
  const { mutate: doImport, isPending: isImporting } = useImport();

  const handleToggleStatus = async (user) => {
    const isCurrentlyActive = isEntityActive(user);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateUser({
        id: user.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} user:`, err);
    }
  };

  const handleExport = () => {
    doExport({ type: 'USER', format: 'excel' });
  };

  const handleImport = ({ file, mapping }) => {
    doImport(
      { type: 'USER', file, mapping },
      {
        onSuccess: () => {
          setIsImportOpen(false);
          refetch();
          alert('Import started successfully! Users will be created with default password "Welcome123!".');
        },
        onError: (err) => alert('Import failed: ' + err.message)
      }
    );
  };

  const renderRowActions = (user) => {
    const isActive = isEntityActive(user);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Profile', onClick: () => navigate(`/users/${user.id}`) },
          { type: 'edit', label: 'Edit User', onClick: () => navigate(`/users/${user.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(user),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(user),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', user.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <>
      <ListPage
        title="Users"
        description="Manage system users, roles and access assignments."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' }, 
          { label: 'Administration' }, 
          { label: 'Users' }
        ]}
        createTo="/users/new"
        createLabel="Add User"
        canCreate={true}
        showSupplierFilter={false}
        searchPlaceholder="Search by username, email or name..."
        searchValue={list.searchInput}
        onSearchChange={list.setSearchInput}
        onRefresh={refetch}
        onExport={handleExport}
        onImport={() => setIsImportOpen(true)}
        quickFilters={[
          { value: 'ALL', label: 'All' },
          { value: 'ACTIVE', label: 'Active' },
          { value: 'INACTIVE', label: 'Inactive' },
          { value: 'SUSPENDED', label: 'Suspended' },
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
        onRowClick={(user) => navigate(`/users/${user.id}`)}
        emptyTitle="No users found"
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
        title="Users"
        isLoading={isImporting}
        onImport={handleImport}
        fields={[
          { key: 'username', label: 'Username', required: true },
          { key: 'email', label: 'Email Address', required: true },
          { key: 'full_name', label: 'Full Name' },
        ]}
      />
    </>
  );
};

export default UserListPage;
