import React, { lazy } from 'react';

const BranchListPage = lazy(() => import('./pages/BranchListPage'));
const BranchCreatePage = lazy(() => import('./pages/BranchCreatePage'));
const BranchEditPage = lazy(() => import('./pages/BranchEditPage'));

export const branchRoutes = [
  {
    path: 'branches',
    children: [
      { index: true, element: <BranchListPage /> },
      { path: 'new', element: <BranchCreatePage /> },
      { path: ':id', element: <BranchEditPage /> },
      { path: ':id/edit', element: <BranchEditPage /> },
    ]
  }
];
