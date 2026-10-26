import React, { lazy } from 'react';

const WarehouseListPage = lazy(() => import('./pages/WarehouseListPage'));
const WarehouseCreatePage = lazy(() => import('./pages/WarehouseCreatePage'));
const WarehouseEditPage = lazy(() => import('./pages/WarehouseEditPage'));

export const warehouseRoutes = [
  {
    path: 'warehouses',
    children: [
      { index: true, element: <WarehouseListPage /> },
      { path: 'new', element: <WarehouseCreatePage /> },
      { path: ':id', element: <WarehouseEditPage /> },
      { path: ':id/edit', element: <WarehouseEditPage /> },
    ]
  }
];
