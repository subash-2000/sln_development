import { lazy } from 'react';

const JobWorkRegisterPage = lazy(() => import('./pages/JobWorkRegisterPage'));
const JobWorkCreatePage = lazy(() => import('./pages/JobWorkCreatePage'));
const JobWorkEditPage = lazy(() => import('./pages/JobWorkEditPage'));
const JobWorkDCSPage = lazy(() => import('./pages/JobWorkDCSPage'));

export const jobWorkRoutes = [
  {
    path: 'job-work/register',
    children: [
      { index: true, element: <JobWorkRegisterPage /> },
      { path: 'new', element: <JobWorkCreatePage /> },
      { path: ':id', element: <JobWorkEditPage /> },
      { path: ':id/edit', element: <JobWorkEditPage /> },
    ],
  },
  {
    path: 'job-work/dcs',
    children: [
      { index: true, element: <JobWorkDCSPage /> },
      { path: ':id', element: <JobWorkDCSPage /> },
    ],
  }
];
