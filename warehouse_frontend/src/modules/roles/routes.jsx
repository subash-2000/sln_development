import React, { lazy } from 'react';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

const RoleListPage = lazy(() => import('./pages/RoleListPage'));
const PermissionListPage = lazy(() => import('./pages/PermissionListPage'));

export const roleRoutes = [
  {
    path: 'roles',
    children: [
      { index: true, element: <RoleListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="Create Role"
            moduleName="Roles"
            backTo="/roles"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'System' },
              { label: 'Roles & Permissions', to: '/roles' },
              { label: 'Create Role' },
            ]}
          />
        ),
      },
      { path: 'permissions', element: <PermissionListPage /> },
    ],
  },
];
