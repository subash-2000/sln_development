import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Button from '../ui/Button';

/**
 * Enterprise Pagination Component
 */
const Pagination = ({
  currentPage = 1,
  pageSize = 25,
  totalRecords = 0,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
}) => {
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const startRecord = (currentPage - 1) * pageSize + 1;
  const endRecord = Math.min(currentPage * pageSize, totalRecords);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-xl space-y-3 sm:space-y-0">
      <div className="text-sm text-gray-600">
        Showing <span className="font-semibold">{startRecord}</span> to <span className="font-semibold">{endRecord}</span> of <span className="font-semibold">{totalRecords}</span> records
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-600">Rows per page:</label>
          <select 
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 p-1.5 outline-none"
          >
            {pageSizeOptions.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="icon"
            isDisabled={currentPage === 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            <ChevronLeft size={18} />
          </Button>
          
          <div className="flex items-center px-4 text-sm font-medium text-gray-700">
            Page {currentPage} of {totalPages}
          </div>

          <Button
            variant="ghost"
            size="icon"
            isDisabled={currentPage === totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            <ChevronRight size={18} />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Pagination;
