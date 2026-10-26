import React from 'react';
import BinListPage from './pages/BinListPage';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

export const binRoutes = [
  {
    path: 'bins',
    children: [
      { index: true, element: <BinListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="Add Bin"
            moduleName="Bins"
            backTo="/bins"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Warehouse' },
              { label: 'Bins', to: '/bins' },
              { label: 'Add Bin' },
            ]}
          />
        ),
      },
      { path: ':id', element: <BinListPage /> },
    ],
  },
];
