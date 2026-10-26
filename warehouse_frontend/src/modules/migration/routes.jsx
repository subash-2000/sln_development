import React, { lazy } from 'react';

const MigrationPage = lazy(() => import('./pages/MigrationPage'));

export const migrationRoutes = [
  {
    path: 'migration',
    children: [
      { index: true, element: <MigrationPage /> }
    ]
  }
];
