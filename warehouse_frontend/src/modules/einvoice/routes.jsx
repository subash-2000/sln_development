import React, { lazy } from 'react';

const EInvoicePage = lazy(() => import('./pages/EInvoicePage'));

export const einvoiceRoutes = [{ path: 'finance/einvoice', element: <EInvoicePage /> }];
