import React, { lazy } from 'react';

const TransporterListPage = lazy(() => import('./pages/TransporterListPage'));
const TransporterCreatePage = lazy(() => import('./pages/TransporterCreatePage'));
const TransporterEditPage = lazy(() => import('./pages/TransporterEditPage'));

export const transportRoutes = [
  {
    path: 'transport',
    children: [
      { index: true, element: <TransporterListPage /> },
      { path: 'vehicles', element: <TransporterListPage /> },
      { path: 'new', element: <TransporterCreatePage /> },
      { path: ':id', element: <TransporterEditPage /> },
      { path: ':id/edit', element: <TransporterEditPage /> },
    ],
  },
];
