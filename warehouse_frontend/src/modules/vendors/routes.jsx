import React, { lazy } from 'react';

const VendorListPage = lazy(() => import('./pages/VendorListPage'));
const VendorCreatePage = lazy(() => import('./pages/VendorCreatePage'));
const VendorEditPage = lazy(() => import('./pages/VendorEditPage'));

export const vendorRoutes = [
  {
    path: 'suppliers',
    children: [
      { index: true, element: <VendorListPage /> },
      { path: 'new', element: <VendorCreatePage /> },
      { path: ':id', element: <VendorEditPage /> },
      { path: ':id/edit', element: <VendorEditPage /> },
    ]
  }
];
