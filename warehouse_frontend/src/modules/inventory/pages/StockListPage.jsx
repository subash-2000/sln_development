import React, { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useListState } from '../../../hooks/use-list-state';
import { useStock } from '../hooks/use-inventory';
import ListPage from '../../../components/tables/ListPage';
import { useVendors } from '../../vendors/hooks/use-vendors';
import { useAuthStore } from '../../../store/auth.store';
import InventoryMasterExportMenu from '../components/InventoryMasterExportMenu';
import StockListToolbar from '../components/StockListToolbar';
import { inventoryApi } from '../api/inventory.api';
import StatusBadge from '../../../components/ui/StatusBadge';

const StockListPage = () => {
  const navigate = useNavigate();
  const initialColumns = [
    { key: 'product_name', label: 'Product', sortable: true },
    { key: 'sku', label: 'SKU', widthClass: 'w-32' },
    { key: 'batch_number', label: 'Batch/Lot', widthClass: 'w-28' },
    { key: 'vendor_name', label: 'Supplier' },
    { key: 'warehouse_name', label: 'Warehouse' },
    { key: 'location_name', label: 'Location' },
    { key: 'quantity_on_hand', label: 'Total Qty', type: 'quantity', widthClass: 'w-28' },
    { key: 'quantity_available', label: 'Available Qty', type: 'quantity', widthClass: 'w-28' },
    { key: 'quantity_reserved', label: 'Reserved Qty', type: 'quantity', widthClass: 'w-28' },
    { key: 'uom_code', label: 'UOM', widthClass: 'w-20' },
    { key: 'age_label', label: 'Age', widthClass: 'w-24' },
    {
      key: 'age_status',
      label: 'Stock status',
      widthClass: 'w-28',
      render: (value) => <StatusBadge status={value} className="whitespace-nowrap" />,
    },
    { key: 'last_movement_at', label: 'Updated', type: 'datetime' },
  ];

  const list = useListState({
    initialColumns
  });

  const vendorId = useAuthStore((s) => s.vendorContext) || '';
  const productId = list.filters.product_id || '';

  const handleProductChange = useCallback(
    (id) => {
      list.setFilters(id ? { product_id: id } : {});
    },
    [list.setFilters]
  );

  const { data: vendorsData } = useVendors({ page_size: 200 });
  const { data, isLoading, isFetching, error, refetch } = useStock(list.params);

  useEffect(() => {
    inventoryApi.warmInventoryMasterExport('ALL');
  }, []);

  useEffect(() => {
    const vendor = (vendorsData?.items || []).find((v) => v.id === vendorId);
    const code = vendor?.code?.toUpperCase();
    if (code && ['AASHITA', 'MANU', 'NHB'].includes(code)) {
      inventoryApi.warmInventoryMasterExport(code);
    }
  }, [vendorId, vendorsData]);

  return (
    <ListPage
      title="Current Stock"
      description="On-hand, available and reserved quantities across all warehouses."
      breadcrumbs={[
        { label: 'Dashboard', to: '/dashboard' }, 
        { label: 'Inventory' }, 
        { label: 'Stock' }
      ]}
      canCreate={false}
      customToolbar={
        <StockListToolbar
          searchPlaceholder="Search batch or reference..."
          searchValue={list.searchInput}
          onSearchChange={list.setSearchInput}
          productId={productId}
          onProductChange={handleProductChange}
          columns={list.columns}
          onToggleColumn={list.toggleColumn}
          onRefresh={refetch}
          inventoryMenu={
            <InventoryMasterExportMenu
              vendorId={vendorId}
              vendors={vendorsData?.items || []}
              onImported={refetch}
            />
          }
        />
      }
      quickFilters={[
        { value: 'ALL', label: 'All Stock' },
        { value: 'AVAILABLE', label: 'Available' },
        { value: 'RESERVED', label: 'Reserved' },
        { value: 'LOW_STOCK', label: 'Low Stock' },
      ]}
      quickFilterValue={list.status}
      onQuickFilterChange={list.setStatus}
      columns={list.columns}
      onToggleColumn={list.toggleColumn}
      rows={data?.items || []}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRetry={refetch}
      sorting={{ key: list.sortBy, order: list.sortOrder }}
      onSort={list.handleSort}
      hasActiveFilters={list.hasActiveFilters || Boolean(productId)}
      emptyTitle="No stock records found"
      pagination={{
        currentPage: list.page,
        pageSize: list.pageSize,
        totalRecords: data?.pagination?.total || 0,
        onPageChange: list.setPage,
        onPageSizeChange: list.setPageSize,
      }}
      onRowClick={(row) => {
        if (row.batch_number) {
          navigate(`/inventory/lots/${encodeURIComponent(row.batch_number)}`);
        }
      }}
    />
  );
};

export default StockListPage;
