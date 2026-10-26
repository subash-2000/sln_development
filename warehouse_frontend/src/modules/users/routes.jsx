import React, { lazy } from 'react';

const UserListPage = lazy(() => import('./pages/UserListPage'));
const UserCreatePage = lazy(() => import('./pages/UserCreatePage'));
const UserEditPage = lazy(() => import('./pages/UserEditPage'));

export const userRoutes = [
  {
    path: 'users',
    children: [
      { index: true, element: <UserListPage /> },
      { path: 'new', element: <UserCreatePage /> },
      { path: ':id', element: <UserEditPage /> },
      { path: ':id/edit', element: <UserEditPage /> },
      // Detail page could be added later
    ]
  }
];
