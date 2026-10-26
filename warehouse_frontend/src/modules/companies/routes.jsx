import React, { lazy } from 'react';

const CompanyListPage = lazy(() => import('./pages/CompanyListPage'));
const CompanyCreatePage = lazy(() => import('./pages/CompanyCreatePage'));
const CompanyEditPage = lazy(() => import('./pages/CompanyEditPage'));

export const companyRoutes = [
  {
    path: 'companies',
    children: [
      { index: true, element: <CompanyListPage /> },
      { path: 'new', element: <CompanyCreatePage /> },
      { path: ':id', element: <CompanyEditPage /> },
      { path: ':id/edit', element: <CompanyEditPage /> },
    ]
  }
];
