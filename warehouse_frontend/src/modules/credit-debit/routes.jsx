import { lazy } from 'react';
const CreditDebitPage = lazy(() => import('./pages/CreditDebitPage'));
export const creditDebitRoutes = [{ path: 'finance/credit-debit', element: <CreditDebitPage /> }];
