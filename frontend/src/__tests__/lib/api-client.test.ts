/**
 * Tests for API Client
 */

import Cookies from "js-cookie";
import {
  api,
  ApiError,
  AuthError,
  TokenManager,
} from "@/lib/api/client";

// Mock js-cookie
jest.mock("js-cookie", () => ({
  get: jest.fn(),
  set: jest.fn(),
  remove: jest.fn(),
}));

const mockedCookies = Cookies as jest.Mocked<typeof Cookies>;

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Store original environment
const originalEnv = process.env.NODE_ENV;

beforeEach(() => {
  jest.clearAllMocks();
  mockFetch.mockReset();
});

afterAll(() => {
  process.env.NODE_ENV = originalEnv;
});

describe("ApiError", () => {
  it("should create error with message and status", () => {
    const error = new ApiError("Not found", 404);

    expect(error.message).toBe("Not found");
    expect(error.status).toBe(404);
    expect(error.name).toBe("ApiError");
  });

  it("should create error with code and details", () => {
    const error = new ApiError("Validation failed", 400, "VALIDATION_ERROR", {
      field: "email",
    });

    expect(error.status).toBe(400);
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.details).toEqual({ field: "email" });
  });

  it("should be an instance of Error", () => {
    const error = new ApiError("Test error", 500);

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
  });
});

describe("AuthError", () => {
  it("should create auth error with default message", () => {
    const error = new AuthError();

    expect(error.message).toBe("Authentication required");
    expect(error.status).toBe(401);
    expect(error.code).toBe("AUTH_ERROR");
    expect(error.name).toBe("AuthError");
  });

  it("should create auth error with custom message", () => {
    const error = new AuthError("Token expired");

    expect(error.message).toBe("Token expired");
    expect(error.status).toBe(401);
  });

  it("should be an instance of ApiError", () => {
    const error = new AuthError();

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toBeInstanceOf(AuthError);
  });
});

describe("TokenManager", () => {
  describe("getAccessToken", () => {
    it("should return token from cookies", () => {
      mockedCookies.get.mockReturnValue("test-access-token");

      const token = TokenManager.getAccessToken();

      expect(mockedCookies.get).toHaveBeenCalledWith("access_token");
      expect(token).toBe("test-access-token");
    });

    it("should return null when no token", () => {
      mockedCookies.get.mockReturnValue(undefined);

      const token = TokenManager.getAccessToken();

      expect(token).toBeNull();
    });
  });

  describe("getRefreshToken", () => {
    it("should return refresh token from cookies", () => {
      mockedCookies.get.mockReturnValue("test-refresh-token");

      const token = TokenManager.getRefreshToken();

      expect(mockedCookies.get).toHaveBeenCalledWith("refresh_token");
      expect(token).toBe("test-refresh-token");
    });

    it("should return null when no refresh token", () => {
      mockedCookies.get.mockReturnValue(undefined);

      const token = TokenManager.getRefreshToken();

      expect(token).toBeNull();
    });
  });

  describe("setTokens", () => {
    it("should set access token with correct options", () => {
      TokenManager.setTokens("new-access-token");

      expect(mockedCookies.set).toHaveBeenCalledWith(
        "access_token",
        "new-access-token",
        expect.objectContaining({
          expires: 1 / 24,
          sameSite: "lax",
          path: "/",
        })
      );
    });

    it("should set both tokens when refresh token provided", () => {
      TokenManager.setTokens("new-access-token", "new-refresh-token");

      expect(mockedCookies.set).toHaveBeenCalledTimes(2);
      expect(mockedCookies.set).toHaveBeenCalledWith(
        "access_token",
        "new-access-token",
        expect.any(Object)
      );
      expect(mockedCookies.set).toHaveBeenCalledWith(
        "refresh_token",
        "new-refresh-token",
        expect.objectContaining({
          expires: 7,
          sameSite: "lax",
          path: "/",
        })
      );
    });
  });

  describe("clearTokens", () => {
    it("should remove both tokens", () => {
      TokenManager.clearTokens();

      expect(mockedCookies.remove).toHaveBeenCalledWith("access_token", {
        path: "/",
      });
      expect(mockedCookies.remove).toHaveBeenCalledWith("refresh_token", {
        path: "/",
      });
    });
  });

  describe("isAuthenticated", () => {
    it("should return true when access token exists", () => {
      mockedCookies.get.mockReturnValue("test-token");

      expect(TokenManager.isAuthenticated()).toBe(true);
    });

    it("should return false when no access token", () => {
      mockedCookies.get.mockReturnValue(undefined);

      expect(TokenManager.isAuthenticated()).toBe(false);
    });
  });

  describe("refreshAccessToken", () => {
    it("should return false when no refresh token", async () => {
      mockedCookies.get.mockReturnValue(undefined);

      const result = await TokenManager.refreshAccessToken();

      expect(result).toBe(false);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should refresh token successfully", async () => {
      mockedCookies.get.mockReturnValue("test-refresh-token");
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
      });

      const result = await TokenManager.refreshAccessToken();

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/refresh"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ refresh_token: "test-refresh-token" }),
        })
      );
      expect(mockedCookies.set).toHaveBeenCalled();
    });

    it("should return false when refresh fails", async () => {
      mockedCookies.get.mockReturnValue("test-refresh-token");
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
      });

      const result = await TokenManager.refreshAccessToken();

      expect(result).toBe(false);
    });

    it("should return false on network error", async () => {
      mockedCookies.get.mockReturnValue("test-refresh-token");
      mockFetch.mockRejectedValue(new Error("Network error"));

      const result = await TokenManager.refreshAccessToken();

      expect(result).toBe(false);
    });
  });
});

describe("api", () => {
  beforeEach(() => {
    mockedCookies.get.mockReturnValue("test-token");
  });

  describe("get", () => {
    it("should make GET request", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, name: "Test" }),
      });

      const result = await api.get("/users/1");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/users/1"),
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            Authorization: "Bearer test-token",
          }),
        })
      );
      expect(result).toEqual({ id: 1, name: "Test" });
    });

    it("should include query params", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });

      await api.get("/users", { params: { page: 1, limit: 10 } });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/page=1.*limit=10|limit=10.*page=1/),
        expect.any(Object)
      );
    });

    it("should skip undefined params", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });

      await api.get("/users", { params: { page: 1, filter: undefined } });

      const callUrl = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("page=1");
      expect(callUrl).not.toContain("filter");
    });
  });

  describe("post", () => {
    it("should make POST request with body", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 201,
        json: () => Promise.resolve({ id: 1 }),
      });

      const result = await api.post("/users", { name: "Test" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/users"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ name: "Test" }),
        })
      );
      expect(result).toEqual({ id: 1 });
    });

    it("should make POST request without body", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true }),
      });

      await api.post("/logout");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/logout"),
        expect.objectContaining({
          method: "POST",
          body: undefined,
        })
      );
    });
  });

  describe("put", () => {
    it("should make PUT request", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, name: "Updated" }),
      });

      await api.put("/users/1", { name: "Updated" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/users/1"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ name: "Updated" }),
        })
      );
    });
  });

  describe("patch", () => {
    it("should make PATCH request", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, status: "active" }),
      });

      await api.patch("/users/1", { status: "active" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/users/1"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ status: "active" }),
        })
      );
    });
  });

  describe("delete", () => {
    it("should make DELETE request", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 204,
      });

      await api.delete("/users/1");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/users/1"),
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });

  describe("skipAuth", () => {
    it("should skip authorization header when skipAuth is true", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await api.get("/public", { skipAuth: true });

      const headers = mockFetch.mock.calls[0][1].headers;
      expect(headers.Authorization).toBeUndefined();
    });
  });

  describe("error handling", () => {
    it("should throw ApiError on non-ok response", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "User not found" }),
      });

      await expect(api.get("/users/999")).rejects.toThrow(ApiError);
      await expect(api.get("/users/999")).rejects.toMatchObject({
        message: "User not found",
        status: 404,
      });
    });

    it("should throw AuthError on 401 response", async () => {
      mockedCookies.get.mockReturnValue(undefined);
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Invalid token" }),
      });

      await expect(api.get("/protected", { skipAuth: true })).rejects.toThrow(
        AuthError
      );
    });

    it("should use default message when error body cannot be parsed", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("Invalid JSON")),
      });

      await expect(api.get("/error")).rejects.toMatchObject({
        message: "Request failed: 500",
        status: 500,
      });
    });

    it("should extract message from different error body formats", async () => {
      // Test with 'message' field
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ message: "Bad request" }),
      });

      await expect(api.get("/test")).rejects.toMatchObject({
        message: "Bad request",
      });
    });
  });

  describe("token refresh", () => {
    it("should retry request after successful token refresh on 401", async () => {
      // First call returns 401
      // After refresh, second call succeeds
      let callCount = 0;
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes("/auth/refresh")) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                access_token: "new-token",
                refresh_token: "new-refresh",
              }),
          };
        }
        callCount++;
        if (callCount === 1) {
          return {
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: "Token expired" }),
          };
        }
        return {
          ok: true,
          status: 200,
          json: () => Promise.resolve({ data: "success" }),
        };
      });

      mockedCookies.get.mockImplementation((key: string) => {
        if (key === "access_token") return "old-token";
        if (key === "refresh_token") return "refresh-token";
        return undefined;
      });

      const result = await api.get("/protected");

      expect(result).toEqual({ data: "success" });
      expect(mockFetch).toHaveBeenCalledTimes(3); // Original + refresh + retry
    });

    it("should throw AuthError when refresh fails", async () => {
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes("/auth/refresh")) {
          return { ok: false, status: 401 };
        }
        return {
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "Token expired" }),
        };
      });

      mockedCookies.get.mockImplementation((key: string) => {
        if (key === "access_token") return "old-token";
        if (key === "refresh_token") return "refresh-token";
        return undefined;
      });

      await expect(api.get("/protected")).rejects.toThrow(AuthError);
      expect(mockedCookies.remove).toHaveBeenCalled();
    });
  });

  describe("204 No Content", () => {
    it("should handle 204 response without body", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 204,
      });

      const result = await api.delete("/users/1");

      expect(result).toBeNull();
    });
  });
});
