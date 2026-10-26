import React from 'react';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

/**
 * Common Loader Component
 */
const Loader = ({ fullPage = false, className, message = 'Loading...' }) => {
  const content = (
    <div className={clsx('flex flex-col items-center justify-center space-y-4', className)}>
      <Loader2 className="h-10 w-10 animate-spin text-primary-600" />
      <span className="text-sm font-medium text-gray-500">{message}</span>
    </div>
  );

  if (fullPage) {
    return (
      <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
};

export default Loader;
