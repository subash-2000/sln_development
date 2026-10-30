import React, { lazy } from 'react';

const ProductListPage = lazy(() => import('./pages/ProductListPage'));
const ProductCreatePage = lazy(() => import('./pages/ProductCreatePage'));
const ProductEditPage = lazy(() => import('./pages/ProductEditPage'));
const CategoryListPage = lazy(() => import('./categories/pages/CategoryListPage'));
const CategoryCreatePage = lazy(() => import('./categories/pages/CategoryCreatePage'));
const CategoryEditPage = lazy(() => import('./categories/pages/CategoryEditPage'));
const UomListPage = lazy(() => import('./uom/pages/UomListPage'));
const UomCreatePage = lazy(() => import('./uom/pages/UomCreatePage'));
const UomEditPage = lazy(() => import('./uom/pages/UomEditPage'));

export const productRoutes = [
  {
    path: 'products',
    children: [
      { index: true, element: <ProductListPage /> },
      { path: 'new', element: <ProductCreatePage /> },
      { path: 'categories', element: <CategoryListPage /> },
      { path: 'categories/new', element: <CategoryCreatePage /> },
      { path: 'categories/:id', element: <CategoryEditPage /> },
      { path: 'categories/:id/edit', element: <CategoryEditPage /> },
      { path: 'uom', element: <UomListPage /> },
      { path: 'uom/new', element: <UomCreatePage /> },
      { path: 'uom/:id', element: <UomEditPage /> },
      { path: 'uom/:id/edit', element: <UomEditPage /> },
      { path: ':id', element: <ProductEditPage /> },
      { path: ':id/edit', element: <ProductEditPage /> },
    ],
  },
  {
    path: 'masters/products',
    children: [
      { index: true, element: <ProductListPage /> },
      { path: 'new', element: <ProductCreatePage /> },
      { path: 'categories', element: <CategoryListPage /> },
      { path: 'categories/new', element: <CategoryCreatePage /> },
      { path: 'categories/:id', element: <CategoryEditPage /> },
      { path: 'categories/:id/edit', element: <CategoryEditPage /> },
      { path: 'uom', element: <UomListPage /> },
      { path: 'uom/new', element: <UomCreatePage /> },
      { path: 'uom/:id', element: <UomEditPage /> },
      { path: 'uom/:id/edit', element: <UomEditPage /> },
      { path: ':id', element: <ProductEditPage /> },
      { path: ':id/edit', element: <ProductEditPage /> },
    ],
  },
];
