import React, { lazy } from 'react';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

const BillingListPage = lazy(() => import('./pages/BillingListPage'));

export const billingRoutes = [
  {
    path: 'finance/billing',
    children: [
      { index: true, element: <BillingListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="Create Billing Contract"
            moduleName="Billing"
            backTo="/finance/billing"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Finance' },
              { label: 'Billing Contracts', to: '/finance/billing' },
              { label: 'New Billing' },
            ]}
          />
        ),
      },
      { path: ':id', element: <BillingListPage /> },
    ],
  },
];
