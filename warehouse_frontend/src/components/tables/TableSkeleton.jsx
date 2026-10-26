import React from 'react';

/**
 * Loading Skeleton for Table
 */
const TableSkeleton = ({ columns = 5, rows = 5 }) => {
  return (
    <div className="w-full flex flex-col space-y-4 animate-pulse">
      <div className="h-10 bg-gray-200 rounded-lg w-full"></div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex space-x-4 p-4 border-b border-gray-100">
            {Array.from({ length: columns }).map((_, j) => (
              <div key={j} className="h-4 bg-gray-100 rounded w-full"></div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TableSkeleton;
