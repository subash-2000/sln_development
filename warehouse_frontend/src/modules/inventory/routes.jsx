import React from 'react';
import StockListPage from './pages/StockListPage';
import TransactionListPage from './pages/TransactionListPage';
import TransactionDetailPage from './pages/TransactionDetailPage';
import LedgerListPage from './pages/LedgerListPage';
import LotDetailPage from './pages/LotDetailPage';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

export const inventoryRoutes = [
  {
    path: 'inventory/stock',
    children: [
      { index: true, element: <StockListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="Adjust Stock"
            moduleName="Inventory Stock"
            backTo="/inventory/stock"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Inventory' },
              { label: 'Stock Levels', to: '/inventory/stock' },
              { label: 'Adjust Stock' },
            ]}
          />
        ),
      },
      { path: ':id', element: <StockListPage /> },
    ],
  },
  {
    path: 'inventory/transactions',
    children: [
      { index: true, element: <TransactionListPage /> },
      {
        path: 'new',
        element: (
          <UnderDevelopmentPage
            title="New Stock Transaction"
            moduleName="Stock Transactions"
            backTo="/inventory/transactions"
            breadcrumbs={[
              { label: 'Dashboard', to: '/dashboard' },
              { label: 'Inventory' },
              { label: 'Stock Transactions', to: '/inventory/transactions' },
              { label: 'New Transaction' },
            ]}
          />
        ),
      },
      { path: ':id', element: <TransactionDetailPage /> },
    ],
  },
  {
    path: 'inventory/lots/:lotNumber',
    element: <LotDetailPage />,
  },
  {
    path: 'inventory/ledger',
    children: [
      { index: true, element: <LedgerListPage /> },
      { path: ':id', element: <LedgerListPage /> },
    ],
  },
];
