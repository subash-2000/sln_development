import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useListState } from '../../../../hooks/use-list-state';
import { useCategories, useUpdateCategory, useDeleteCategory } from '../hooks/use-categories';
import ListPage from '../../../../components/tables/ListPage';
import RowActions from '../../../../components/tables/RowActions';
import ConfirmDialog from '../../../../components/modals/ConfirmDialog';
import CategoryViewModal from '../components/CategoryViewModal';
import { isEntityActive } from '../../../../constants/status';

const CategoryListPage = () => {
  const navigate = useNavigate();
  const [viewingCategory, setViewingCategory] = useState(null);
  const [deletingCategory, setDeletingCategory] = useState(null);
  const [actionError, setActionError] = useState(null);

  const initialColumns = [
    { key: 'code', label: 'Code', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Category Name', sortable: true },
    { key: 'description', label: 'Description' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'updated_at', label: 'Last Updated', type: 'datetime' },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns,
  });

  const { data, isLoading, isFetching, error, refetch } = useCategories(list.params);
  const { mutateAsync: updateCategory } = useUpdateCategory();
  const { mutateAsync: deleteCategory, isPending: isDeleting } = useDeleteCategory();

  const handleToggleStatus = async (category) => {
    setActionError(null);
    const isCurrentlyActive = isEntityActive(category);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCategory({
        id: category.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} category:`, err);
      setActionError(
        err?.response?.data?.detail ||
        err?.message ||
        `Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} category.`
      );
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingCategory) return;
    setActionError(null);
    try {
      await deleteCategory(deletingCategory.id);
      setDeletingCategory(null);
      refetch();
    } catch (err) {
      console.error('Failed to delete category:', err);
      setActionError(
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to delete category. It may have products or sub-categories assigned.'
      );
      setDeletingCategory(null);
    }
  };

  const renderRowActions = (category) => {
    const isActive = isEntityActive(category);
    return (
      <RowActions
        actions={[
          {
            type: 'view',
            label: 'View Category',
            onClick: () => setViewingCategory(category),
          },
          {
            type: 'edit',
            label: 'Edit Category',
            onClick: () => navigate(`/products/categories/${category.id}/edit`),
          },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(category),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(category),
            hidden: isActive,
          },
          {
            type: 'delete',
            label: 'Delete',
            onClick: () => {
              setActionError(null);
              setDeletingCategory(category);
            },
            variant: 'danger',
          },
        ]}
      />
    );
  };

  return (
    <div className="space-y-4">
      {actionError && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
          <span>{actionError}</span>
          <button
            type="button"
            onClick={() => setActionError(null)}
            className="ml-auto text-xs text-red-600 hover:text-red-800 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      <ListPage
        title="Product Categories"
        description="Manage product category hierarchy for warehouse items."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products', to: '/products' },
          { label: 'Categories' },
        ]}
        createTo="/products/categories/new"
        createLabel="Add Category"
        canCreate={true}
        searchPlaceholder="Search by category code or name..."
        searchValue={list.searchInput}
        onSearchChange={list.setSearchInput}
        onRefresh={refetch}
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
        onRowClick={(category) => setViewingCategory(category)}
        emptyTitle="No categories found"
        pagination={{
          currentPage: list.page,
          pageSize: list.pageSize,
          totalRecords: data?.pagination?.total || 0,
          onPageChange: list.setPage,
          onPageSizeChange: list.setPageSize,
        }}
      />

      {/* Category View Details Modal */}
      <CategoryViewModal
        open={Boolean(viewingCategory)}
        category={viewingCategory}
        allCategories={data?.items || []}
        onClose={() => setViewingCategory(null)}
        onEdit={(cat) => navigate(`/products/categories/${cat.id}/edit`)}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(deletingCategory)}
        title="Delete Product Category"
        description={`Are you sure you want to permanently delete category "${deletingCategory?.name}" (${deletingCategory?.code})? This action cannot be undone.`}
        confirmLabel="Delete Category"
        variant="danger"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeletingCategory(null)}
      />
    </div>
  );
};

export default CategoryListPage;
