import React, { lazy } from 'react';

const ReportListPage = lazy(() => import('./pages/ReportListPage'));
const VehicleReportPage = lazy(() => import('./pages/VehicleReportPage'));
const InwardReportPage = lazy(() => import('./pages/InwardReportPage'));
const OutwardReportPage = lazy(() => import('./pages/OutwardReportPage'));
const DailyStockReportPage = lazy(() => import('./pages/DailyStockReportPage'));
const InvoiceReportPage = lazy(() => import('./pages/InvoiceReportPage'));
const SupplierWiseReportPage = lazy(() => import('./pages/SupplierWiseReportPage'));

export const reportRoutes = [
  {
    path: 'reports',
    children: [
      { index: true, element: <ReportListPage /> },
      { path: 'vehicles', element: <VehicleReportPage /> },
      { path: 'inward', element: <InwardReportPage /> },
      { path: 'outward', element: <OutwardReportPage /> },
      { path: 'daily-stock', element: <DailyStockReportPage /> },
      { path: 'supplier-wise', element: <SupplierWiseReportPage /> },
      { path: 'invoices', element: <InvoiceReportPage /> },
    ]
  }
];
