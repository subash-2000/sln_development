import React from 'react';
import RackListPage from './pages/RackListPage';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

export const rackRoutes = [
  {
    path: 'racks',
    children: [
      { index: true, element: <RackListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="Add Rack"
            moduleName="Racks"
            backTo="/racks"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Warehouse' },
              { label: 'Racks', to: '/racks' },
              { label: 'Add Rack' },
            ]}
          />
        ),
      },
      { path: ':id', element: <RackListPage /> },
    ],
  },
];
