import React, { lazy } from 'react';
import { Navigate } from 'react-router-dom';

const TransactionDetailPage = lazy(() => import('../inventory/pages/TransactionDetailPage'));
const LogisticsOutwardPage = lazy(() => import('./pages/LogisticsOutwardPage'));
const LogisticsOutwardCreatePage = lazy(() => import('./pages/LogisticsOutwardCreatePage'));
const LogisticsDispatchPage = lazy(() => import('./pages/LogisticsDispatchPage'));

export const logisticsRoutes = [
  {
    path: 'logistics/inward',
    children: [
      { index: true, element: <Navigate to="/rings/inward" replace /> },
      { path: 'new', element: <Navigate to="/rings/inward/new" replace /> },
      { path: ':id', element: <TransactionDetailPage /> },
    ],
  },
  {
    path: 'logistics/outward',
    children: [
      { index: true, element: <LogisticsOutwardPage /> },
      { path: 'new', element: <LogisticsOutwardCreatePage /> },
    ],
  },
  {
    path: 'logistics/dispatch',
    element: <LogisticsDispatchPage />,
  },
];
