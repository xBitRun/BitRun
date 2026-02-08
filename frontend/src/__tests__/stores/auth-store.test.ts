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
    const errorMessage = "Invalid credentials";
    mockAuthApi.login.mockRejectedValue(new Error(errorMessage));

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
    expect(state.error).toBe(errorMessage);
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
});
