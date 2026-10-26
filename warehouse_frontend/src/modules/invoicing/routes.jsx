import React, { lazy } from 'react';
import UnderDevelopmentPage from '../../components/common/UnderDevelopmentPage';

const InvoicingListPage = lazy(() => import('./pages/InvoicingListPage'));
const GstReportPage = lazy(() => import('./pages/GstReportPage'));
const NoteListPage = lazy(() => import('./pages/NoteListPage'));

const renderInvoiceUnderDevelopment = () => (
  <UnderDevelopmentPage
    title="Create Invoice"
    moduleName="Invoicing"
    backTo="/finance/invoicing"
    breadcrumbs={[
      { label: 'Dashboard', to: '/dashboard' },
      { label: 'Finance' },
      { label: 'Invoices', to: '/finance/invoicing' },
      { label: 'Create Invoice' },
    ]}
  />
);

const renderNoteUnderDevelopment = () => (
  <UnderDevelopmentPage
    title="Create Credit/Debit Note"
    moduleName="Credit & Debit Notes"
    backTo="/finance/invoicing/notes"
    breadcrumbs={[
      { label: 'Dashboard', to: '/dashboard' },
      { label: 'Finance' },
      { label: 'Notes', to: '/finance/invoicing/notes' },
      { label: 'New Note' },
    ]}
  />
);

export const invoicingRoutes = [
  {
    path: 'finance/invoicing',
    children: [
      { index: true, element: <InvoicingListPage /> },
      { path: 'new', element: renderInvoiceUnderDevelopment() },
      { path: 'gst-reports', element: <GstReportPage /> },
      { path: 'notes', element: <NoteListPage /> },
      { path: 'notes/new', element: renderNoteUnderDevelopment() },
      { path: ':id', element: <InvoicingListPage /> },
    ],
  },
  {
    path: 'invoicing/notes',
    children: [
      { index: true, element: <NoteListPage /> },
      { path: 'new', element: renderNoteUnderDevelopment() },
    ],
  },
];
