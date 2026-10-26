import React from 'react';
import { Outlet } from 'react-router-dom';

/**
 * Layout for Authentication Pages
 */
const AuthLayout = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-600">SLN WMS</h1>
          <p className="text-gray-500 mt-2">Warehouse Management System</p>
        </div>
        <Outlet />
      </div>
    </div>
  );
};

export default AuthLayout;
