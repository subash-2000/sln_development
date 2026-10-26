import { AlertTriangle } from 'lucide-react';
import Button from '../ui/Button';

const ErrorState = ({ title = 'Unable to load data', error, onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="h-12 w-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mb-4">
        <AlertTriangle size={22} />
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="text-sm text-gray-500 mt-1 max-w-md">
        {error?.message || 'Please try again.'}
      </p>
      {error?.requestId && (
        <p className="text-xs text-gray-400 mt-2">Request ID: {error.requestId}</p>
      )}
      {onRetry && (
        <Button className="mt-4" variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
};

export default ErrorState;
