import { NextRequest, NextResponse } from "next/server";
import createIntlMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

// Create the intl middleware
const intlMiddleware = createIntlMiddleware(routing);

// Public routes that don't require authentication
const publicRoutes = ["/", "/login", "/register", "/forgot-password"];

// Auth routes (redirect to home if already logged in)
const authRoutes = ["/login", "/register"];

// Cookie names (must match client-side TokenManager)
const ACCESS_TOKEN_KEY = "access_token";

/**
 * Check if the current path is a public route (doesn't require auth)
 */
function isPublicRoute(pathname: string): boolean {
  // Remove locale prefix if present
  const pathWithoutLocale = pathname.replace(/^\/(en|zh)/, "") || "/";
  return publicRoutes.some((route) =>
    route === "/"
      ? pathWithoutLocale === "/"
      : pathWithoutLocale.startsWith(route)
  );
}

/**
 * Check if the current path is an auth route (login/register)
 */
function isAuthRoute(pathname: string): boolean {
  const pathWithoutLocale = pathname.replace(/^\/(en|zh)/, "") || "/";
  return authRoutes.some((route) => pathWithoutLocale.startsWith(route));
}

/**
 * Get the locale from pathname
 */
function getLocaleFromPath(pathname: string): string {
  const match = pathname.match(/^\/(en|zh)/);
  return match ? match[1] : routing.defaultLocale;
}

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for static files and API routes
  if (
    pathname.includes(".") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api")
  ) {
    return NextResponse.next();
  }

  // Get authentication token from cookies
  const accessToken = request.cookies.get(ACCESS_TOKEN_KEY)?.value;
  const isAuthenticated = !!accessToken;

  // Get locale for redirects
  const locale = getLocaleFromPath(pathname);

  // If user is authenticated and trying to access auth routes, redirect to dashboard
  if (isAuthenticated && isAuthRoute(pathname)) {
    const homeUrl = new URL(`/${locale}/overview`, request.url);
    return NextResponse.redirect(homeUrl);
  }

  // If user is not authenticated and trying to access protected routes, redirect to login
  if (!isAuthenticated && !isPublicRoute(pathname)) {
    const loginUrl = new URL(`/${locale}/login`, request.url);
    // Preserve the original URL as callback
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Run intl middleware for locale handling
  return intlMiddleware(request);
}

export const config = {
  // Match all paths except static files and api
  matcher: [
    "/",
    "/(zh|en)/:path*",
    "/((?!_next|api|.*\\..*).*)",
  ],
};
