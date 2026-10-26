import React, { lazy } from 'react';

const AuditLogPage = lazy(() => import('./pages/AuditLogPage'));

export const auditRoutes = [
  {
    path: 'audit',
    children: [
      { index: true, element: <AuditLogPage /> }
    ]
  }
];
