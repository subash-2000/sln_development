import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../../components/ui/Button';
import { ServerCrash } from 'lucide-react';

const ServerErrorPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center h-20 w-20 bg-orange-100 text-orange-600 rounded-full mb-6">
          <ServerCrash size={40} />
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Server Error</h1>
        <p className="text-gray-500 mt-4">
          Something went wrong on our end. We're working to fix it. Please try again later.
        </p>
        <div className="mt-8">
          <Button 
            variant="primary" 
            onClick={() => window.location.reload()}
          >
            Refresh Page
          </Button>
          <div className="mt-4">
            <Link to="/dashboard" className="text-sm text-primary-600 font-medium hover:underline">
              Return to dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServerErrorPage;
