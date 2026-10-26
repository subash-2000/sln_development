import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      permissions: [],
      companyContext: null,
      branchContext: null,
      vendorContext: null,

      setTokens: (accessToken, refreshToken) =>
        set({
          accessToken,
          refreshToken: refreshToken ?? get().refreshToken,
          isAuthenticated: Boolean(accessToken),
        }),

      setAuth: (user, accessToken, refreshToken, permissions = []) => {
        const defaultCompany = user?.access_assignments?.[0]?.company_id || null;
        const defaultBranch = user?.access_assignments?.[0]?.branch_id || null;
        set({
          user,
          accessToken,
          refreshToken: refreshToken ?? get().refreshToken,
          permissions,
          isAuthenticated: true,
          companyContext: get().companyContext || defaultCompany,
          branchContext: get().branchContext || defaultBranch,
        });
      },

      setProfile: (user, permissions = []) => {
        const defaultCompany = user?.access_assignments?.[0]?.company_id || null;
        const defaultBranch = user?.access_assignments?.[0]?.branch_id || null;
        set({
          user,
          permissions,
          companyContext: get().companyContext || defaultCompany,
          branchContext: get().branchContext || defaultBranch,
        });
      },

      clearAuth: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          permissions: [],
          isAuthenticated: false,
          companyContext: null,
          branchContext: null,
          vendorContext: null,
        }),

      setContext: (companyId, branchId) =>
        set({ companyContext: companyId, branchContext: branchId }),

      setVendorContext: (vendorId) => set({ vendorContext: vendorId || null }),

      hasPermission: (permission) => {
        const { permissions, user } = get();
        if (user?.is_superuser) return true;
        if (permissions.includes('*')) return true;
        return permissions.includes(permission);
      },
    }),
    {
      name: 'wms-auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        permissions: state.permissions,
        companyContext: state.companyContext,
        branchContext: state.branchContext,
        vendorContext: state.vendorContext,
      }),
    }
  )
);
