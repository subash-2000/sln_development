import React from 'react';
import { Bell, User, LogOut, ChevronDown } from 'lucide-react';
import { useAuthStore } from '../../store/auth.store';
import { useAuth } from '../../hooks/use-auth';
import TopMenu from './TopMenu';

const Navbar = () => {
  const { user } = useAuthStore();
  const { logout } = useAuth();
  
  return (
    <div className="flex flex-col bg-white border-b border-gray-200 sticky top-0 z-20">
      <header className="h-14 flex items-center justify-between px-6 border-b border-gray-50">
        {/* Left side: Logo & Brand */}
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold">W</div>
            <span className="font-bold text-lg text-gray-900 tracking-tight">SLN WMS</span>
          </div>
        </div>

        {/* Right side: User & Notifications */}
        <div className="flex items-center space-x-2">
          <button className="p-2 text-gray-400 hover:bg-gray-50 rounded-lg relative">
            <Bell size={18} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
          </button>

          <div className="h-6 w-px bg-gray-200 mx-2"></div>

          <div className="relative group">
            <button className="flex items-center space-x-3 p-1 rounded-lg hover:bg-gray-50 transition-all">
              <div className="h-8 w-8 bg-primary-100 text-primary-700 rounded-lg flex items-center justify-center font-bold text-xs">
                {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="text-left hidden sm:block mr-2">
                <p className="text-xs font-bold text-gray-900 leading-tight">{user?.full_name || user?.username || 'User'}</p>
                <p className="text-[10px] text-gray-500 uppercase tracking-tight font-medium">
                  {user?.is_superuser ? 'Super Admin' : (user?.roles?.[0] || 'Member')}
                </p>
              </div>
              <ChevronDown size={12} className="text-gray-400" />
            </button>
            
            {/* User Dropdown */}
            <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-100 rounded-xl shadow-lg py-1 opacity-0 group-hover:opacity-100 invisible group-hover:visible transition-all duration-200 z-50">
              <a href="#profile" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                <User size={14} className="mr-3 text-gray-400" /> Profile
              </a>
              <button 
                onClick={logout}
                className="w-full flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <LogOut size={14} className="mr-3" /> Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="relative z-20 min-h-11 px-2 flex items-center overflow-visible border-b border-gray-50">
        <TopMenu />
      </div>
    </div>
  );
};

export default Navbar;
