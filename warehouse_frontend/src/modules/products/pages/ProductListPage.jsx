import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useProducts, useUpdateProduct } from '../hooks/use-products';
import { useImport, useExport } from '../../../hooks/use-migration';
import ListPage from '../../../components/tables/ListPage';
import RowActions from '../../../components/tables/RowActions';
import { isEntityActive } from '../../../constants/status';
import ImportModal from '../../../components/tables/ImportModal';

const ProductListPage = () => {
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);
  
  const initialColumns = [
    { key: 'sku', label: 'SKU', sortable: true, widthClass: 'w-32' },
    { key: 'name', label: 'Product Name', sortable: true },
    { key: 'part_number', label: 'Part Number', sortable: true, widthClass: 'w-36' },
    {
      key: 'net_weight',
      label: 'Ring Weight',
      sortable: true,
      widthClass: 'w-28',
      render: (value) =>
        value == null || value === ''
          ? '-'
          : Number(value).toLocaleString('en-IN', { maximumFractionDigits: 6 }),
    },
    { key: 'heat_number', label: 'Heat Number', sortable: true, widthClass: 'w-32' },
    { key: 'packing_ratio', label: 'Ratio', sortable: true, widthClass: 'w-24' },
    { key: 'category_name', label: 'Category', sortable: true },
    { key: 'uom_code', label: 'UOM', sortable: true, widthClass: 'w-20' },
    { key: 'hsn_code', label: 'HSN', sortable: true, widthClass: 'w-28' },
    { key: 'status', label: 'Status', type: 'status', sortable: true },
    { key: 'updated_at', label: 'Updated', type: 'datetime', sortable: true },
  ];

  const list = useListState({ 
    defaultSortBy: 'name',
    initialColumns
  });

  const { data, isLoading, isFetching, error, refetch } = useProducts(list.params);
  const { mutateAsync: updateProduct } = useUpdateProduct();
  const { mutate: doExport } = useExport();
  const { mutate: doImport, isPending: isImporting } = useImport();

  const handleToggleStatus = async (product) => {
    const isCurrentlyActive = isEntityActive(product);
    const newStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateProduct({
        id: product.id,
        data: {
          status: newStatus,
          is_active: !isCurrentlyActive,
        },
      });
      refetch();
    } catch (err) {
      console.error(`Failed to ${isCurrentlyActive ? 'deactivate' : 'activate'} product:`, err);
    }
  };

  const handleExport = () => {
    doExport({ type: 'PRODUCT', format: 'excel' });
  };

  const handleImport = ({ file, mapping }) => {
    doImport(
      { type: 'PRODUCT', file, mapping },
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

  const renderRowActions = (product) => {
    const isActive = isEntityActive(product);
    return (
      <RowActions
        actions={[
          { type: 'view', label: 'View Details', onClick: () => navigate(`/products/${product.id}`) },
          { type: 'edit', label: 'Edit Product', onClick: () => navigate(`/products/${product.id}/edit`) },
          {
            type: 'deactivate',
            label: 'Deactivate',
            onClick: () => handleToggleStatus(product),
            hidden: !isActive,
          },
          {
            type: 'activate',
            label: 'Activate',
            onClick: () => handleToggleStatus(product),
            hidden: isActive,
          },
          { type: 'delete', label: 'Delete', onClick: () => console.log('Delete', product.id), variant: 'danger' },
        ]}
      />
    );
  };

  return (
    <>
      <ListPage
        title="Products"
        description="Manage product master data, SKUs, categories and UOMs."
        breadcrumbs={[
          { label: 'Dashboard', to: '/dashboard' },
          { label: 'Masters' },
          { label: 'Products' },
        ]}
        createTo="/products/new"
        createLabel="Add Product"
        canCreate={true}
        searchPlaceholder="Search by SKU, name or HSN code..."
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
        onRowClick={(product) => navigate(`/products/${product.id}`)}
        emptyTitle="No products found"
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
        title="Products"
        isLoading={isImporting}
        onImport={handleImport}
        fields={[
          { key: 'sku', label: 'SKU', required: true },
          { key: 'name', label: 'Name', required: true },
          { key: 'part_number', label: 'Part Number' },
          { key: 'description', label: 'Description' },
          { key: 'hsn_code', label: 'HSN' },
          { key: 'category', label: 'Category' },
          { key: 'uom_code', label: 'UOM' },
          { key: 'net_weight', label: 'Net Weight' },
          { key: 'gross_weight', label: 'Gross Weight' },
          { key: 'barcode', label: 'Barcode' },
          { key: 'is_lot_tracked', label: 'Lot Tracked' },
          { key: 'batch_number', label: 'Batch Number' },
          { key: 'heat_number', label: 'Heat Number' },
          { key: 'gauge_number', label: 'Gauge' },
          { key: 'mill_name', label: 'Mill' },
          { key: 'package_tracking_type', label: 'Pallet or Cotton Box' },
          { key: 'package_tracking_value', label: 'Package Number' },
          { key: 'status', label: 'Status' },
        ]}
        sampleUrl="PRODUCT"
      />
    </>
  );
};

export default ProductListPage;
