/**
 * Tests for Header component
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Polyfill for PointerEvent (needed for Radix UI)
class MockPointerEvent extends Event {
  button: number;
  ctrlKey: boolean;
  pointerType: string;
  constructor(type: string, props: PointerEventInit) {
    super(type, props);
    this.button = props.button ?? 0;
    this.ctrlKey = props.ctrlKey ?? false;
    this.pointerType = props.pointerType ?? "mouse";
  }
}
// @ts-expect-error - polyfill
global.PointerEvent = MockPointerEvent;

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      search: "Search...",
      systemOnline: "System Online",
      myAccount: "My Account",
      settings: "Settings",
      logout: "Logout",
    };
    return translations[key] || key;
  },
}));

// Mock i18n navigation
jest.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} role="link" {...props}>
      {children}
    </a>
  ),
}));

// Mock auth store
const mockLogout = jest.fn().mockResolvedValue(undefined);
const mockAuthStore = {
  user: null as { id: string; email: string; name: string } | null,
  logout: mockLogout,
  isLoading: false,
};

jest.mock("@/stores/auth-store", () => ({
  useAuthStore: () => mockAuthStore,
}));

// Mock theme and language switchers
jest.mock("@/components/layout/theme-switcher", () => ({
  ThemeSwitcher: () => <button>Theme Switcher</button>,
}));

jest.mock("@/components/layout/language-switcher", () => ({
  LanguageSwitcher: () => <button>Language Switcher</button>,
}));

import { Header } from "@/components/layout/header";

describe("Header", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthStore.user = null;
    mockAuthStore.isLoading = false;
  });

  describe("rendering", () => {
    it("should render search input", () => {
      render(<Header />);

      expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
    });

    it("should render theme switcher", () => {
      render(<Header />);

      expect(screen.getByText("Theme Switcher")).toBeInTheDocument();
    });

    it("should render language switcher", () => {
      render(<Header />);

      expect(screen.getByText("Language Switcher")).toBeInTheDocument();
    });

    it("should render system status indicator", () => {
      render(<Header />);

      expect(screen.getByText("System Online")).toBeInTheDocument();
    });
  });

  describe("mobile menu", () => {
    it("should render menu button when onMenuClick is provided", () => {
      const onMenuClick = jest.fn();
      render(<Header onMenuClick={onMenuClick} />);

      // Menu button should exist
      const menuButtons = screen.getAllByRole("button");
      expect(menuButtons.length).toBeGreaterThan(0);
    });

    it("should not render menu button when onMenuClick is not provided", () => {
      render(<Header />);

      // Only theme, language, and user menu buttons
      const buttons = screen.getAllByRole("button");
      // Should not include a menu button
      expect(
        buttons.some((btn) => btn.className.includes("md:hidden"))
      ).toBeFalsy();
    });
  });

  describe("user menu", () => {
    it("should show default avatar when no user", () => {
      render(<Header />);

      // Default initial "U"
      expect(screen.getByText("U")).toBeInTheDocument();
    });

    it("should show user initials from name", () => {
      mockAuthStore.user = {
        id: "1",
        email: "john@example.com",
        name: "John Doe",
      };

      render(<Header />);

      expect(screen.getByText("J")).toBeInTheDocument();
    });

    it("should show user initials from email when no name", () => {
      mockAuthStore.user = {
        id: "1",
        email: "alice@example.com",
        name: "",
      };

      render(<Header />);

      expect(screen.getByText("A")).toBeInTheDocument();
    });

    it("should show user name in menu when available", async () => {
      const user = userEvent.setup();
      mockAuthStore.user = {
        id: "1",
        email: "john@example.com",
        name: "John Doe",
      };

      render(<Header />);

      // Open dropdown
      const avatarButton = screen.getByRole("button", { name: /john/i });
      await user.click(avatarButton);

      await waitFor(() => {
        // User name appears twice: in header button and in dropdown label
        const johnDoeElements = screen.getAllByText("John Doe");
        expect(johnDoeElements.length).toBeGreaterThanOrEqual(2);
        expect(screen.getByText("john@example.com")).toBeInTheDocument();
      });
    });

    it("should show My Account when no user name", async () => {
      const user = userEvent.setup();
      mockAuthStore.user = null;

      render(<Header />);

      // Open dropdown
      const avatarButton = screen.getByText("U").closest("button");
      if (avatarButton) {
        await user.click(avatarButton);
      }

      await waitFor(() => {
        expect(screen.getByText("My Account")).toBeInTheDocument();
      });
    });
  });

  describe("logout", () => {
    it("should call logout when logout is clicked", async () => {
      const user = userEvent.setup();
      mockAuthStore.user = {
        id: "1",
        email: "test@example.com",
        name: "Test User",
      };

      render(<Header />);

      // Open dropdown
      const avatarButton = screen.getByText("T").closest("button");
      if (avatarButton) {
        await user.click(avatarButton);
      }

      await waitFor(() => {
        expect(screen.getByText("Logout")).toBeInTheDocument();
      });

      // Click logout
      await user.click(screen.getByText("Logout"));

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });
    });

    it("should disable logout button when loading", async () => {
      const user = userEvent.setup();
      mockAuthStore.user = {
        id: "1",
        email: "test@example.com",
        name: "Test User",
      };
      mockAuthStore.isLoading = true;

      render(<Header />);

      // Open dropdown
      const avatarButton = screen.getByText("T").closest("button");
      if (avatarButton) {
        await user.click(avatarButton);
      }

      await waitFor(() => {
        const logoutItem = screen.getByText("Logout").closest("[role='menuitem']");
        expect(logoutItem).toHaveAttribute("data-disabled");
      });
    });
  });

  describe("settings link", () => {
    it("should have settings link", async () => {
      const user = userEvent.setup();
      mockAuthStore.user = {
        id: "1",
        email: "test@example.com",
        name: "Test User",
      };

      render(<Header />);

      // Open dropdown
      const avatarButton = screen.getByText("T").closest("button");
      if (avatarButton) {
        await user.click(avatarButton);
      }

      await waitFor(() => {
        expect(screen.getByText("Settings")).toBeInTheDocument();
        // Find the link element containing "Settings" text
        const settingsLink = screen.getByText("Settings").closest("a");
        expect(settingsLink).toHaveAttribute("href", "/settings");
      });
    });
  });

  describe("accessibility", () => {
    it("should have accessible user menu trigger", () => {
      mockAuthStore.user = {
        id: "1",
        email: "test@example.com",
        name: "Test User",
      };

      render(<Header />);

      const avatarButton = screen.getByText("T").closest("button");
      expect(avatarButton).toHaveClass("focus:outline-none");
      expect(avatarButton).toHaveClass("focus-visible:ring-2");
    });
  });
});
