import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/navigation/Navbar';
import { useAuthStore } from '../store/auth.store';
import { useCompanies } from '../modules/companies/hooks/use-companies';
import Loader from '../components/common/Loader';

/**
 * Main Application Layout
 */
const MainLayout = () => {
  const { companyContext, setContext } = useAuthStore();
  const { data: companiesData, isLoading } = useCompanies({ page_size: 10 });
  const companies = companiesData?.items || [];

  // Initialize tenant context if not set
  useEffect(() => {
    if (!companyContext && companies.length > 0) {
      setContext(companies[0].id, null);
    }
  }, [companies, companyContext, setContext]);

  if (isLoading || (!companyContext && companies.length > 0)) {
    return <Loader fullPage message="Initializing workspace..." />;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Navbar (Header + TopMenu) */}
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 flex flex-col">
        <div className="max-w-[1600px] w-full mx-auto flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
