import { lazy } from 'react';

const RingsInwardPage = lazy(() => import('./pages/RingsInwardPage'));
const RingsInwardCreatePage = lazy(() => import('./pages/RingsInwardCreatePage'));
const RingsDocumentDetailPage = lazy(() => import('./pages/RingsDocumentDetailPage'));
const RingsPickPage = lazy(() => import('./pages/RingsPickPage'));
const RingsPickCreatePage = lazy(() => import('./pages/RingsPickCreatePage'));
const RingsDispatchPage = lazy(() => import('./pages/RingsDispatchPage'));
const RingsStockPage = lazy(() => import('./pages/RingsStockPage'));
const RingsSalesPage = lazy(() => import('./pages/RingsSalesPage'));

export const ringsRoutes = [
  {
    path: 'rings/inward',
    children: [
      { index: true, element: <RingsInwardPage /> },
      { path: 'new', element: <RingsInwardCreatePage /> },
      { path: ':id', element: <RingsDocumentDetailPage /> },
    ],
  },
  {
    path: 'rings/picks',
    children: [
      { index: true, element: <RingsPickPage /> },
      { path: 'new', element: <RingsPickCreatePage /> },
      { path: ':id', element: <RingsDocumentDetailPage /> },
    ],
  },
  {
    path: 'rings/dispatch',
    children: [
      { index: true, element: <RingsDispatchPage /> },
      { path: ':id', element: <RingsDocumentDetailPage /> },
    ],
  },
  { path: 'rings/stock', element: <RingsStockPage /> },
  { path: 'rings/sales', element: <RingsSalesPage /> },
];
