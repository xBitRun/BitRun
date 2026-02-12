"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "@/i18n/navigation";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { TokenManager } from "@/lib/api/client";

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * AuthGuard component for client-side route protection.
 *
 * This provides a secondary layer of protection alongside server-side
 * middleware checks. It handles cases where:
 * - Token expires while user is on the page
 * - User manually clears cookies
 * - SPA navigation after authentication state changes
 *
 * NOTE: The full-screen loading state only shows on the initial auth check.
 * Subsequent route changes rely on Next.js loading.tsx for content-area loading,
 * keeping the header and sidebar visible at all times.
 */
export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, checkAuth } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);
  const hasChecked = useRef(false);

  useEffect(() => {
    // Only run the blocking auth check once on initial mount.
    // Subsequent navigations are handled by middleware + Next.js loading.tsx.
    if (hasChecked.current) return;

    const verifyAuth = async () => {
      // Check if access token exists
      if (!TokenManager.isAuthenticated()) {
        // Try to refresh using refresh token
        const refreshed = await TokenManager.refreshAccessToken();
        if (!refreshed) {
          // No valid tokens, redirect to login
          router.replace(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
          return;
        }
      }

      // Skip checkAuth if we already have user info from login response
      // This avoids redundant GET /auth/me after successful login
      if (isAuthenticated && user) {
        hasChecked.current = true;
        setIsChecking(false);
        return;
      }

      // Verify token with backend (only needed on page refresh when store is empty)
      try {
        await checkAuth();
      } catch {
        // Token might be invalid, let middleware handle redirect
      } finally {
        hasChecked.current = true;
        setIsChecking(false);
      }
    };

    verifyAuth();
  }, [pathname, router, checkAuth, isAuthenticated, user]);

  // Only show full-screen loading on the initial auth check.
  // Store's isLoading is intentionally NOT used here to avoid
  // re-blocking the entire layout on subsequent navigations.
  if (isChecking) {
    return (
      fallback || (
        <div className="flex h-screen items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
      )
    );
  }

  // Not authenticated - middleware should handle redirect
  // But we show nothing here to prevent flash of protected content
  if (!isAuthenticated && !TokenManager.isAuthenticated()) {
    return null;
  }

  return <>{children}</>;
}

/**
 * Higher-order component for route protection
 */
export function withAuthGuard<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  return function AuthGuardedComponent(props: P) {
    return (
      <AuthGuard>
        <WrappedComponent {...props} />
      </AuthGuard>
    );
  };
}
