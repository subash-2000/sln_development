import React, { lazy } from 'react';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

const VendorStockListPage = lazy(() => import('./pages/VendorStockListPage'));

const renderUnderDevelopment = () => (
  <UnderDevelopmentPage
    title="New Supplier Stock Agreement"
    moduleName="Supplier Stock Agreements"
    backTo="/inventory/supplier-stock"
    breadcrumbs={[
      { label: 'Dashboard', to: '/dashboard' },
      { label: 'Inventory' },
      { label: 'Supplier Stock Agreements', to: '/inventory/supplier-stock' },
      { label: 'New Agreement' },
    ]}
  />
);

export const vendorStockRoutes = [
  {
    path: 'supplier-stock',
    children: [
      { index: true, element: <VendorStockListPage /> },
      { path: 'new', element: renderUnderDevelopment() },
      { path: ':id', element: <VendorStockListPage /> },
    ],
    permission: 'vendor_stock.view',
  },
  {
    path: 'inventory/supplier-stock',
    children: [
      { index: true, element: <VendorStockListPage /> },
      { path: 'new', element: renderUnderDevelopment() },
      { path: ':id', element: <VendorStockListPage /> },
    ],
    permission: 'vendor_stock.view',
  },
];
