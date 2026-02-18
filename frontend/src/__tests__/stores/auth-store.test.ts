/**
 * Auth Store Tests
 *
 * Tests for the Zustand auth store.
 */

import { act } from "@testing-library/react";
import { useAuthStore } from "@/stores/auth-store";

// Mock the API modules before importing the store
jest.mock("@/lib/api", () => ({
  authApi: {
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
    me: jest.fn(),
  },
  TokenManager: {
    setTokens: jest.fn(),
    clearTokens: jest.fn(),
    isAuthenticated: jest.fn(() => false),
    refreshAccessToken: jest.fn(() => Promise.resolve(false)),
  },
  AuthError: class AuthError extends Error {},
  ApiError: class ApiError extends Error {
    code: string;
    details: Record<string, unknown> | null;
    constructor(message: string, code = "UNKNOWN", details: Record<string, unknown> | null = null) {
      super(message);
      this.code = code;
      this.details = details;
    }
  },
}));

// Get references to the mocked functions
import { authApi, TokenManager } from "@/lib/api";

const mockAuthApi = authApi as jest.Mocked<typeof authApi>;
const mockTokenManager = TokenManager as jest.Mocked<typeof TokenManager>;

describe("Auth Store", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset mock implementations
    mockTokenManager.isAuthenticated.mockReturnValue(false);
    mockTokenManager.refreshAccessToken.mockResolvedValue(false);
    
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  });

  it("should initialize with default state", () => {
    const state = useAuthStore.getState();

    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("should set user and authenticate on successful login", async () => {
    const testUser = {
      id: "test-id",
      email: "test@example.com",
      name: "Test User",
      is_active: true,
      role: "user" as const,
    };

    const tokenResponse = {
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    };

    mockAuthApi.login.mockResolvedValue(tokenResponse);
    mockAuthApi.me.mockResolvedValue(testUser);

    await act(async () => {
      await useAuthStore.getState().login({
        email: "test@example.com",
        password: "password123",
      });
    });

    const state = useAuthStore.getState();
    expect(state.user).toEqual(testUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(mockTokenManager.setTokens).toHaveBeenCalledWith(
      "test-access-token",
      "test-refresh-token"
    );
  });

  it("should clear user on logout", async () => {
    // Setup: First login a user
    const testUser = {
      id: "test-id",
      email: "test@example.com",
      name: "Test User",
      is_active: true,
      role: "user" as const,
    };

    mockAuthApi.login.mockResolvedValue({
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
    mockAuthApi.me.mockResolvedValue(testUser);
    mockAuthApi.logout.mockResolvedValue({ message: "Logged out" });

    await act(async () => {
      await useAuthStore.getState().login({
        email: "test@example.com",
        password: "password123",
      });
    });

    // Verify logged in state
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    // Now logout
    await act(async () => {
      await useAuthStore.getState().logout();
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(mockTokenManager.clearTokens).toHaveBeenCalled();
  });

  it("should set error on login failure", async () => {
    mockAuthApi.login.mockRejectedValue(new Error("Invalid credentials"));

    await act(async () => {
      try {
        await useAuthStore.getState().login({
          email: "test@example.com",
          password: "wrongpassword",
        });
      } catch {
        // Expected to throw
      }
    });

    const state = useAuthStore.getState();
    // Store now sets a structured AuthErrorInfo object instead of a string
    expect(state.error).toEqual({ code: "LOGIN_FAILED" });
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("should clear error", async () => {
    // First set an error
    mockAuthApi.login.mockRejectedValue(new Error("Test error"));

    await act(async () => {
      try {
        await useAuthStore.getState().login({
          email: "test@example.com",
          password: "wrong",
        });
      } catch {
        // Expected
      }
    });

    expect(useAuthStore.getState().error).not.toBeNull();

    // Now clear it
    act(() => {
      useAuthStore.getState().clearError();
    });

    expect(useAuthStore.getState().error).toBeNull();
  });

  it("should handle login with ApiError details", async () => {
    const { ApiError } = await import("@/lib/api");
    const apiError = new ApiError("Invalid credentials", 401, "AUTH_INVALID_CREDENTIALS", {
      remaining_attempts: 2,
      remaining_minutes: 5,
    });

    mockAuthApi.login.mockRejectedValue(apiError);

    await act(async () => {
      try {
        await useAuthStore.getState().login({
          email: "test@example.com",
          password: "wrong",
        });
      } catch {
        // Expected
      }
    });

    const state = useAuthStore.getState();
    expect(state.error).toEqual({
      code: "AUTH_INVALID_CREDENTIALS",
      remaining_attempts: 2,
      remaining_minutes: 5,
    });
  });

  it("should handle login when me() fails but login succeeds", async () => {
    const tokenResponse = {
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    };

    mockAuthApi.login.mockResolvedValue(tokenResponse);
    mockAuthApi.me.mockRejectedValue(new Error("Failed to fetch user"));

    await act(async () => {
      await useAuthStore.getState().login({
        email: "test@example.com",
        password: "password123",
      });
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it("should register and auto-login successfully", async () => {
    const testUser = {
      id: "test-id",
      email: "new@example.com",
      name: "New User",
      is_active: true,
      role: "user" as const,
    };

    const tokenResponse = {
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    };

    mockAuthApi.register.mockResolvedValue(testUser);
    mockAuthApi.login.mockResolvedValue(tokenResponse);
    mockAuthApi.me.mockResolvedValue(testUser);

    await act(async () => {
      await useAuthStore.getState().register({
        email: "new@example.com",
        password: "password123",
        name: "New User",
        invite_code: "TEST123",
      });
    });

    const state = useAuthStore.getState();
    expect(state.user).toEqual(testUser);
    expect(state.isAuthenticated).toBe(true);
    expect(mockAuthApi.register).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
      name: "New User",
    });
    expect(mockAuthApi.login).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
    });
  });

  it("should handle register failure with ApiError", async () => {
    const { ApiError } = await import("@/lib/api");
    const apiError = new ApiError("Email exists", 400, "AUTH_EMAIL_EXISTS");

    mockAuthApi.register.mockRejectedValue(apiError);

    await act(async () => {
      try {
        await useAuthStore.getState().register({
          email: "existing@example.com",
          password: "password123",
          name: "User",
          invite_code: "TEST123",
        });
      } catch {
        // Expected
      }
    });

    const state = useAuthStore.getState();
    expect(state.error).toEqual({ code: "AUTH_EMAIL_EXISTS" });
    expect(state.isAuthenticated).toBe(false);
  });

  it("should handle register failure with generic error", async () => {
    mockAuthApi.register.mockRejectedValue(new Error("Network error"));

    await act(async () => {
      try {
        await useAuthStore.getState().register({
          email: "test@example.com",
          password: "password123",
          name: "User",
          invite_code: "TEST123",
        });
      } catch {
        // Expected
      }
    });

    const state = useAuthStore.getState();
    expect(state.error).toEqual({ code: "REGISTER_FAILED" });
  });

  it("should handle register when me() fails after auto-login", async () => {
    const testUser = {
      id: "test-id",
      email: "new@example.com",
      name: "New User",
      is_active: true,
      role: "user" as const,
    };
    const tokenResponse = {
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    };

    mockAuthApi.register.mockResolvedValue(testUser);
    mockAuthApi.login.mockResolvedValue(tokenResponse);
    mockAuthApi.me.mockRejectedValue(new Error("Failed to fetch user"));

    await act(async () => {
      await useAuthStore.getState().register({
        email: "new@example.com",
        password: "password123",
        name: "New User",
        invite_code: "TEST123",
      });
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(true);
  });

  it("should handle logout even when API call fails", async () => {
    mockAuthApi.logout.mockRejectedValue(new Error("Network error"));

    await act(async () => {
      await useAuthStore.getState().logout();
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(mockTokenManager.clearTokens).toHaveBeenCalled();
  });

  it("should checkAuth successfully when token exists", async () => {
    const testUser = {
      id: "test-id",
      email: "test@example.com",
      name: "Test User",
      is_active: true,
      role: "user" as const,
    };

    mockTokenManager.isAuthenticated.mockReturnValue(true);
    mockAuthApi.me.mockResolvedValue(testUser);

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    expect(state.user).toEqual(testUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it("should refresh token when checkAuth called without access token", async () => {
    const testUser = {
      id: "test-id",
      email: "test@example.com",
      name: "Test User",
      is_active: true,
      role: "user" as const,
    };

    mockTokenManager.isAuthenticated.mockReturnValue(false);
    mockTokenManager.refreshAccessToken.mockResolvedValue(true);
    mockAuthApi.me.mockResolvedValue(testUser);

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    expect(state.user).toEqual(testUser);
    expect(state.isAuthenticated).toBe(true);
    expect(mockTokenManager.refreshAccessToken).toHaveBeenCalled();
  });

  it("should handle checkAuth when refresh fails", async () => {
    mockTokenManager.isAuthenticated.mockReturnValue(false);
    mockTokenManager.refreshAccessToken.mockResolvedValue(false);

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });

  it("should handle checkAuth with AuthError", async () => {
    const { AuthError } = await import("@/lib/api");
    const authError = new AuthError("Unauthorized");

    mockTokenManager.isAuthenticated.mockReturnValue(true);
    mockAuthApi.me.mockRejectedValue(authError);

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(mockTokenManager.clearTokens).toHaveBeenCalled();
  });

  it("should handle checkAuth with network error but keep authenticated state", async () => {
    const testUser = {
      id: "test-id",
      email: "test@example.com",
      name: "Test User",
      is_active: true,
      role: "user" as const,
    };

    // Set initial state with user
    useAuthStore.setState({
      user: testUser,
      isAuthenticated: true,
    });

    mockTokenManager.isAuthenticated.mockReturnValue(true);
    mockAuthApi.me.mockRejectedValue(new Error("Network error"));

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    // Should keep existing user and authenticated state
    expect(state.user).toEqual(testUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it("should handle checkAuth with network error when no token", async () => {
    mockTokenManager.isAuthenticated.mockReturnValue(false);
    mockTokenManager.refreshAccessToken.mockResolvedValue(false);

    await act(async () => {
      await useAuthStore.getState().checkAuth();
    });

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
  });
});
