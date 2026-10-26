import React, { lazy } from 'react';

const LocationListPage = lazy(() => import('./pages/LocationListPage'));
const LocationCreatePage = lazy(() => import('./pages/LocationCreatePage'));
const LocationEditPage = lazy(() => import('./pages/LocationEditPage'));

export const locationRoutes = [
  {
    path: 'locations',
    children: [
      { index: true, element: <LocationListPage /> },
      { path: 'new', element: <LocationCreatePage /> },
      { path: ':id', element: <LocationEditPage /> },
      { path: ':id/edit', element: <LocationEditPage /> },
    ]
  }
];
