import React from 'react';
import { GitBranch, ChevronDown } from 'lucide-react';
import { useBranches } from '../../modules/branches/hooks/use-branches';
import { useAuthStore } from '../../store/auth.store';

const BranchFilter = () => {
  const { companyContext, branchContext, setContext } = useAuthStore();
  const { data: branchesData, isLoading } = useBranches({ 
    page_size: 100, 
    company_id: companyContext 
  });
  const branches = branchesData?.items || [];

  const handleChange = (e) => {
    setContext(companyContext, e.target.value);
  };

  if (!companyContext) return null;

  if (isLoading && branches.length === 0) {
    return (
      <div className="h-9 w-32 bg-gray-100 animate-pulse rounded-lg"></div>
    );
  }

  return (
    <div className="relative flex items-center">
      <GitBranch size={16} className="absolute left-3 text-gray-400 pointer-events-none" />
      <select
        value={branchContext || ''}
        onChange={handleChange}
        className="h-9 pl-9 pr-8 py-1.5 text-xs font-semibold bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none appearance-none cursor-pointer hover:bg-white transition-all max-w-[180px] truncate"
      >
        <option value="">All Branches</option>
        {branches.map((branch) => (
          <option key={branch.id} value={branch.id}>
            {branch.name}
          </option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2.5 text-gray-400 pointer-events-none" />
    </div>
  );
};

export default BranchFilter;
