import React, { lazy } from 'react';

const CustomerListPage = lazy(() => import('./pages/CustomerListPage'));
const CustomerCreatePage = lazy(() => import('./pages/CustomerCreatePage'));
const CustomerEditPage = lazy(() => import('./pages/CustomerEditPage'));
const BuyerListPage = lazy(() => import('./pages/BuyerListPage'));
const BuyerCreatePage = lazy(() => import('./pages/BuyerCreatePage'));
const BuyerEditPage = lazy(() => import('./pages/BuyerEditPage'));

export const customerRoutes = [
  {
    path: 'customers',
    children: [
      { index: true, element: <CustomerListPage /> },
      { path: 'new', element: <CustomerCreatePage /> },
      { path: ':id', element: <CustomerEditPage /> },
      { path: ':id/edit', element: <CustomerEditPage /> },
    ]
  },
  {
    path: 'buyers',
    children: [
      { index: true, element: <BuyerListPage /> },
      { path: 'new', element: <BuyerCreatePage /> },
      { path: ':id', element: <BuyerEditPage /> },
      { path: ':id/edit', element: <BuyerEditPage /> },
    ]
  }
];
