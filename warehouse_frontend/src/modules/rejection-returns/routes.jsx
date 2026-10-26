import React, { lazy } from 'react';

const ReturnsListPage = lazy(() => import('./pages/ReturnsListPage'));
const ReturnCreatePage = lazy(() => import('./pages/ReturnCreatePage'));
const ReturnDetailPage = lazy(() => import('./pages/ReturnDetailPage'));

export const returnsRoutes = [
  {
    path: 'rejection-returns',
    children: [
      { index: true, element: <ReturnsListPage /> },
      { path: 'new', element: <ReturnCreatePage /> },
      { path: 'create', element: <ReturnCreatePage /> },
      { path: ':id', element: <ReturnDetailPage /> },
    ],
  },
  {
    path: 'returns/list',
    children: [
      { index: true, element: <ReturnsListPage /> },
      { path: 'new', element: <ReturnCreatePage /> },
      { path: ':id', element: <ReturnDetailPage /> },
    ],
  },
];
