/**
 * API Client for BITRUN Backend
 *
 * Handles all HTTP requests with authentication, error handling, and retries.
 */

import Cookies from 'js-cookie';

// API Configuration
// API v1 is the current stable version
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

// Error types
export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export class AuthError extends ApiError {
  constructor(message: string = 'Authentication required') {
    super(message, 401, 'AUTH_ERROR');
    this.name = 'AuthError';
  }
}

// Token management
export const TokenManager = {
  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return Cookies.get(TOKEN_KEY) || null;
  },

  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return Cookies.get(REFRESH_KEY) || null;
  },

  setTokens(accessToken: string, refreshToken?: string): void {
    // Access token expires in 60 minutes (match backend JWT expiry)
    Cookies.set(TOKEN_KEY, accessToken, {
      expires: 1/24,  // 60 minutes (1 hour)
      sameSite: 'lax',  // Allow cross-site GET requests
      secure: process.env.NODE_ENV === 'production',
      path: '/',  // Ensure available across entire site
    });

    if (refreshToken) {
      // Refresh token expires in 7 days
      Cookies.set(REFRESH_KEY, refreshToken, {
        expires: 7,
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
        path: '/',
      });
    }
  },

  clearTokens(): void {
    Cookies.remove(TOKEN_KEY, { path: '/' });
    Cookies.remove(REFRESH_KEY, { path: '/' });
  },

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  },

  /**
   * Refresh access token using refresh token
   * Returns true if refresh was successful, false otherwise
   */
  async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },
};

// Request options type
interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
}

// Response type
interface ApiResponse<T> {
  data: T;
  status: number;
}

/**
 * Build URL with query parameters
 */
function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  // Concatenate base URL with path (handles paths starting with /)
  const fullPath = path.startsWith('/') ? `${API_BASE_URL}${path}` : `${API_BASE_URL}/${path}`;
  const url = new URL(fullPath);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

// Track if we're currently refreshing to prevent multiple refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (process.env.NODE_ENV === "test") return;
  window.location.href = "/login";
}

/**
 * Main fetch wrapper with auth and error handling
 */
async function fetchApi<T>(
  path: string,
  options: RequestOptions = {},
  isRetry = false
): Promise<ApiResponse<T>> {
  const { params, skipAuth = false, ...fetchOptions } = options;

  // Build headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers || {}),
  };

  // Add auth header if not skipped
  if (!skipAuth) {
    const token = TokenManager.getAccessToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  // Build URL
  const url = buildUrl(path, params);

  // Make request
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle response
  if (!response.ok) {
    // Try to parse error body
    let errorData: { detail?: string | Record<string, unknown>; message?: string; code?: string } = {};
    try {
      errorData = await response.json();
    } catch {
      // Ignore parse errors
    }

    // Handle structured error detail from backend: { code: "AUTH_...", remaining_attempts?: number, ... }
    let message: string;
    let errorCode: string | undefined;
    let details: Record<string, unknown> | undefined;
    
    if (errorData.detail && typeof errorData.detail === 'object') {
      // Structured error from backend
      const structuredError = errorData.detail as Record<string, unknown>;
      errorCode = structuredError.code as string;
      message = errorCode || `Request failed: ${response.status}`;
      details = structuredError;
    } else {
      // Simple string error
      message = (errorData.detail as string) || errorData.message || `Request failed: ${response.status}`;
      errorCode = errorData.code;
    }

    if (response.status === 401 && !skipAuth && !isRetry) {
      // Try to refresh token (only once)
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = TokenManager.refreshAccessToken();
      }

      const refreshed = await refreshPromise;
      isRefreshing = false;
      refreshPromise = null;

      if (refreshed) {
        // Retry original request with new token
        return fetchApi<T>(path, options, true);
      }

      // Refresh failed, clear tokens and redirect to login
      TokenManager.clearTokens();
      redirectToLogin();
      throw new AuthError(message);
    }

    if (response.status === 401) {
      TokenManager.clearTokens();
      redirectToLogin();
      throw new AuthError(message);
    }

    throw new ApiError(message, response.status, errorCode, details);
  }

  // Parse successful response
  const data = response.status === 204 ? null : await response.json();

  return { data: data as T, status: response.status };
}

/**
 * API Client with typed methods
 */
export const api = {
  /**
   * GET request
   */
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const { data } = await fetchApi<T>(path, { ...options, method: 'GET' });
    return data;
  },

  /**
   * POST request
   */
  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { data } = await fetchApi<T>(path, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
    return data;
  },

  /**
   * PUT request
   */
  async put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { data } = await fetchApi<T>(path, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
    return data;
  },

  /**
   * PATCH request
   */
  async patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { data } = await fetchApi<T>(path, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
    return data;
  },

  /**
   * DELETE request
   */
  async delete<T>(path: string, options?: RequestOptions): Promise<T> {
    const { data } = await fetchApi<T>(path, { ...options, method: 'DELETE' });
    return data;
  },
};

export default api;
