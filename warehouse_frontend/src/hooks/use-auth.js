import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/auth.store';
import { authService } from '../services/auth/auth.service';

export const useAuth = () => {
  const queryClient = useQueryClient();
  const storedUser = useAuthStore((state) => state.user);
  const { setAuth, setProfile, setTokens, clearAuth, isAuthenticated } = useAuthStore();

  const userProfile = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authService.getCurrentUser,
    enabled: isAuthenticated,
    retry: false,
    onSuccess: (profile) => {
      setProfile(profile, profile?.permissions || []);
    },
  });

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const profile = await authService.getCurrentUser();
      setAuth(profile, tokens.access_token, tokens.refresh_token, profile.permissions || []);
      queryClient.invalidateQueries();
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSettled: () => {
      clearAuth();
      queryClient.clear();
    },
  });

  return {
    login: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,
    logout: logoutMutation.mutateAsync,
    isLoggingOut: logoutMutation.isPending,
    user: userProfile.data || storedUser,
    isLoadingUser: userProfile.isLoading,
  };
};
