/**
 * Authentication Store
 *
 * Manages user authentication state with Zustand.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { authApi, TokenManager, AuthError, ApiError } from '@/lib/api';
import type { LoginRequest, RegisterRequest, UserResponse } from '@/lib/api';

/**
 * Structured auth error for i18n support.
 * The code is used to look up the translated message in the frontend.
 */
export interface AuthErrorInfo {
  code: string;
  remaining_attempts?: number;
  remaining_minutes?: number;
}

interface AuthState {
  // State
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: AuthErrorInfo | null;

  // Actions
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login
      login: async (data: LoginRequest) => {
        set({ isLoading: true, error: null });

        try {
          const tokenResponse = await authApi.login(data);

          // Store tokens
          TokenManager.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

          // Fetch user info after login
          try {
            const user = await authApi.me();
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch {
            // If fetching user info fails, still mark as authenticated
            // User info will be fetched on next checkAuth
            set({
              user: null,
              isAuthenticated: true,
              isLoading: false,
            });
          }
        } catch (err) {
          // Extract structured error info from ApiError
          let errorInfo: AuthErrorInfo;
          if (err instanceof ApiError && err.details) {
            errorInfo = {
              code: err.code || 'LOGIN_FAILED',
              remaining_attempts: err.details.remaining_attempts as number | undefined,
              remaining_minutes: err.details.remaining_minutes as number | undefined,
            };
          } else {
            errorInfo = { code: 'LOGIN_FAILED' };
          }
          set({ error: errorInfo, isLoading: false });
          throw err;
        }
      },

      // Register - after registration, auto-login
      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });

        try {
          // Registration returns user info but no tokens
          await authApi.register(data);

          // Auto-login after successful registration
          const tokenResponse = await authApi.login({
            email: data.email,
            password: data.password,
          });

          TokenManager.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

          // Fetch user info after login
          try {
            const user = await authApi.me();
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            });
          } catch {
            // If fetching user info fails, still mark as authenticated
            set({
              user: null,
              isAuthenticated: true,
              isLoading: false,
            });
          }
        } catch (err) {
          // Extract structured error info from ApiError
          let errorInfo: AuthErrorInfo;
          if (err instanceof ApiError && err.code) {
            errorInfo = { code: err.code };
          } else {
            errorInfo = { code: 'REGISTER_FAILED' };
          }
          set({ error: errorInfo, isLoading: false });
          throw err;
        }
      },

      // Logout
      logout: async () => {
        set({ isLoading: true });

        try {
          await authApi.logout();
        } catch {
          // Ignore errors on logout
        } finally {
          TokenManager.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      // Check authentication status and fetch user info
      checkAuth: async () => {
        // First check if access token exists
        if (!TokenManager.isAuthenticated()) {
          // Try to refresh using refresh token
          const refreshed = await TokenManager.refreshAccessToken();
          if (!refreshed) {
            set({ isAuthenticated: false, user: null });
            return;
          }
        }

        set({ isLoading: true });

        try {
          // Fetch current user info
          const user = await authApi.me();
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (err) {
          if (err instanceof AuthError) {
            TokenManager.clearTokens();
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
            });
          } else {
            // Network error but tokens exist - keep authenticated state
            // but don't update user info
            const currentState = get();
            set({
              isAuthenticated: TokenManager.isAuthenticated(),
              user: currentState.user, // Keep existing user info
              isLoading: false
            });
          }
        }
      },

      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      // Sync localStorage state with actual Cookie token state on hydration
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          // Hydration error - state may be corrupted, reset to safe defaults
          return;
        }
        if (state) {
          // Check if Cookie token exists
          const hasToken = TokenManager.isAuthenticated();

          if (state.isAuthenticated && !hasToken) {
            // localStorage says logged in, but no token in Cookie
            // This can happen if Cookie expired or was cleared
            // We need to reset the state
            state.isAuthenticated = false;
            state.user = null;
          } else if (!state.isAuthenticated && hasToken) {
            // Token exists but state says not authenticated
            // This can happen if localStorage was cleared but Cookie remains
            state.isAuthenticated = true;
          }
        }
      },
    }
  )
);
