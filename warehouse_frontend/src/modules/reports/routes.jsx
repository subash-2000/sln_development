import React, { lazy } from 'react';

const ReportListPage = lazy(() => import('./pages/ReportListPage'));

export const reportRoutes = [
  {
    path: 'reports',
    children: [
      { index: true, element: <ReportListPage /> }
    ]
  }
];
