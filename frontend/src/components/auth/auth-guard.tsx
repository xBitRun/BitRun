"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
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
 */
export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAuth, isLoading } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const verifyAuth = async () => {
      const locale = pathname.startsWith("/zh") ? "zh" : "en";

      // Check if access token exists
      if (!TokenManager.isAuthenticated()) {
        // Try to refresh using refresh token
        const refreshed = await TokenManager.refreshAccessToken();
        if (!refreshed) {
          // No valid tokens, redirect to login
          router.replace(`/${locale}/login?callbackUrl=${encodeURIComponent(pathname)}`);
          return;
        }
      }

      // Verify token with backend (optional - can be skipped for performance)
      try {
        await checkAuth();
      } catch {
        // Token might be invalid, let middleware handle redirect
      } finally {
        setIsChecking(false);
      }
    };

    verifyAuth();
  }, [pathname, router, checkAuth]);

  // Still checking authentication
  if (isChecking || isLoading) {
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
