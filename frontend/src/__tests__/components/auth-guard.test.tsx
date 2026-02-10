/**
 * Tests for AuthGuard component
 */

import { render, screen, waitFor } from "@testing-library/react";
import React from "react";

// Mock i18n navigation (auth-guard imports from @/i18n/navigation, not next/navigation)
const mockReplace = jest.fn();
jest.mock("@/i18n/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: jest.fn(),
    back: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => "/en/dashboard",
  Link: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock token manager
const mockIsAuthenticated = jest.fn();
const mockRefreshAccessToken = jest.fn();

jest.mock("@/lib/api/client", () => ({
  TokenManager: {
    isAuthenticated: () => mockIsAuthenticated(),
    refreshAccessToken: () => mockRefreshAccessToken(),
  },
}));

// Mock auth store
const mockCheckAuth = jest.fn();
const mockAuthStore = {
  isAuthenticated: false,
  checkAuth: mockCheckAuth,
  isLoading: false,
};

jest.mock("@/stores/auth-store", () => ({
  useAuthStore: () => mockAuthStore,
}));

// Import component after mocks
import { AuthGuard, withAuthGuard } from "@/components/auth/auth-guard";

describe("AuthGuard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore.isAuthenticated = false;
    mockAuthStore.isLoading = false;
  });

  it("should render loading state initially", () => {
    mockIsAuthenticated.mockReturnValue(true);
    mockCheckAuth.mockResolvedValue(undefined);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("should render custom fallback when provided", () => {
    mockIsAuthenticated.mockReturnValue(true);
    mockCheckAuth.mockResolvedValue(undefined);

    render(
      <AuthGuard fallback={<div>Custom Loading</div>}>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByText("Custom Loading")).toBeInTheDocument();
  });

  it("should render children when authenticated", async () => {
    mockIsAuthenticated.mockReturnValue(true);
    mockCheckAuth.mockResolvedValue(undefined);
    mockAuthStore.isAuthenticated = true;

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("should redirect to login when not authenticated", async () => {
    mockIsAuthenticated.mockReturnValue(false);
    mockRefreshAccessToken.mockResolvedValue(false);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining("/login")
      );
    });
  });

  it("should try to refresh token when access token is missing", async () => {
    mockIsAuthenticated.mockReturnValue(false);
    mockRefreshAccessToken.mockResolvedValue(true);
    mockCheckAuth.mockResolvedValue(undefined);
    mockAuthStore.isAuthenticated = true;

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockRefreshAccessToken).toHaveBeenCalled();
    });
  });

  it("should redirect when refresh token fails", async () => {
    mockIsAuthenticated.mockReturnValue(false);
    mockRefreshAccessToken.mockResolvedValue(false);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining("/login?callbackUrl=")
      );
    });
  });

  it("should include callback URL in redirect", async () => {
    mockIsAuthenticated.mockReturnValue(false);
    mockRefreshAccessToken.mockResolvedValue(false);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining(encodeURIComponent("/en/dashboard"))
      );
    });
  });

  it("should handle checkAuth error gracefully", async () => {
    mockIsAuthenticated.mockReturnValue(true);
    mockCheckAuth.mockRejectedValue(new Error("Token invalid"));
    mockAuthStore.isAuthenticated = true;

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    // Should still render children even if checkAuth fails
    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("should return null when not authenticated and not loading", async () => {
    mockIsAuthenticated.mockReturnValue(false);
    mockRefreshAccessToken.mockResolvedValue(false);
    mockAuthStore.isAuthenticated = false;

    const { container } = render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    // Wait for redirect to be called
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalled();
    });

    // Content should not be visible
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });
});

describe("withAuthGuard HOC", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore.isAuthenticated = true;
    mockAuthStore.isLoading = false;
    mockIsAuthenticated.mockReturnValue(true);
    mockCheckAuth.mockResolvedValue(undefined);
  });

  it("should wrap component with AuthGuard", async () => {
    const TestComponent = () => <div>Test Component</div>;
    const WrappedComponent = withAuthGuard(TestComponent);

    render(<WrappedComponent />);

    await waitFor(() => {
      expect(screen.getByText("Test Component")).toBeInTheDocument();
    });
  });

  it("should pass props to wrapped component", async () => {
    interface TestProps {
      message: string;
    }
    const TestComponent = ({ message }: TestProps) => <div>{message}</div>;
    const WrappedComponent = withAuthGuard(TestComponent);

    render(<WrappedComponent message="Hello World" />);

    await waitFor(() => {
      expect(screen.getByText("Hello World")).toBeInTheDocument();
    });
  });
});
