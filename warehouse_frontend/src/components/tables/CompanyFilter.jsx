import React from 'react';
import { Building2, ChevronDown } from 'lucide-react';
import { useCompanies } from '../../modules/companies/hooks/use-companies';
import { useAuthStore } from '../../store/auth.store';

const CompanyFilter = () => {
  const { companyContext, setContext } = useAuthStore();
  const { data: companiesData, isLoading } = useCompanies({ page_size: 100 });
  const companies = companiesData?.items || [];

  const handleChange = (e) => {
    setContext(e.target.value, null);
  };

  if (isLoading && companies.length === 0) {
    return (
      <div className="h-8 w-24 bg-gray-100 animate-pulse rounded-lg"></div>
    );
  }

  return (
    <div className="relative flex items-center group">
      <select
        value={companyContext || ''}
        onChange={handleChange}
        className="h-8 pl-2 pr-7 text-[11px] font-bold bg-white border border-gray-200 rounded-lg focus:ring-1 focus:ring-primary-500 outline-none appearance-none cursor-pointer hover:border-gray-300 transition-all max-w-[140px] truncate text-gray-700 uppercase tracking-tight"
      >
        {companies.map((company) => (
          <option key={company.id} value={company.id}>
            {company.name}
          </option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-2 text-gray-400 pointer-events-none group-hover:text-gray-600" />
    </div>
  );
};

export default CompanyFilter;
