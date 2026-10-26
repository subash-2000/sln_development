import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../../components/ui/Button';
import { ShieldAlert } from 'lucide-react';

const ForbiddenPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center h-20 w-20 bg-red-100 text-red-600 rounded-full mb-6">
          <ShieldAlert size={40} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Access Forbidden</h1>
        <p className="text-gray-500 mt-4">
          You do not have permission to access this resource. If you believe this is an error, please contact your administrator.
        </p>
        <div className="mt-8 flex items-center justify-center space-x-4">
          <Link to="/dashboard">
            <Button variant="secondary">Back to Dashboard</Button>
          </Link>
          <Button variant="primary">Request Access</Button>
        </div>
      </div>
    </div>
  );
};

export default ForbiddenPage;
