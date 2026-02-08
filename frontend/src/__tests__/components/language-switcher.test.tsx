/**
 * Tests for LanguageSwitcher component
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Polyfill for PointerEvent (needed for Radix UI DropdownMenu)
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

// Mock i18n navigation
const mockReplace = jest.fn();
jest.mock("@/i18n/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: jest.fn(),
    back: jest.fn(),
  }),
  usePathname: () => "/dashboard",
  Link: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

import { LanguageSwitcher } from "@/components/layout/language-switcher";

describe("LanguageSwitcher", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render the trigger button", () => {
    render(<LanguageSwitcher />);

    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
  });

  it("should display current locale flag", () => {
    render(<LanguageSwitcher />);

    // Default locale is "en" (from jest.setup.ts mock), should show 🇺🇸
    expect(screen.getByText("🇺🇸")).toBeInTheDocument();
  });

  it("should open dropdown with locale options on click", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("English")).toBeInTheDocument();
      expect(screen.getByText("中文")).toBeInTheDocument();
    });
  });

  it("should call router.replace when selecting a locale", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("中文")).toBeInTheDocument();
    });

    await user.click(screen.getByText("中文"));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard", {
        locale: "zh",
      });
    });
  });

  it("should show both locale flags in dropdown", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      // Both flags should be visible in menu items
      expect(screen.getByText("🇨🇳")).toBeInTheDocument();
      const usFlags = screen.getAllByText("🇺🇸");
      expect(usFlags.length).toBeGreaterThanOrEqual(1);
    });
  });
});
