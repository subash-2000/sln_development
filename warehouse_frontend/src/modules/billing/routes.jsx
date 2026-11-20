import React, { lazy } from 'react';
import { creditDebitRoutes } from '../credit-debit/routes';

const BillingListPage = lazy(() => import('./pages/BillingListPage'));
const CustomerPricingPage = lazy(() => import('./pages/CustomerPricingPage'));
const BillingGeneratePage = lazy(() => import('./pages/BillingGeneratePage'));
const BillingDetailPage = lazy(() => import('./pages/BillingDetailPage'));
const SalesTaxTrackingPage = lazy(() => import('./pages/SalesTaxTrackingPage'));

export const billingRoutes = [
  {
    path: 'finance/billing',
    children: [
      { index: true, element: <BillingListPage /> },
      {
        path: 'new',
        element: <BillingGeneratePage />,
      },
      { path: ':id', element: <BillingDetailPage /> },
    ],
  },
  ...creditDebitRoutes,
  { path: 'finance/customer-pricing', element: <CustomerPricingPage /> },
  { path: 'finance/sales-tax-invoices', element: <SalesTaxTrackingPage /> },
];
