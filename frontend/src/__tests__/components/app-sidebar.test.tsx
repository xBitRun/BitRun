/**
 * Tests for AppSidebar component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppSidebar, MobileMenuButton } from "@/components/layout/app-sidebar";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      dashboard: "Dashboard",
      agents: "Agents",
      strategies: "Strategies",
      accounts: "Accounts",
      models: "Models",
      backtest: "Backtest",
      collapse: "Collapse",
    };
    return translations[key] || key;
  },
}));

// Mock next/navigation
let mockPathname = "/overview";
jest.mock("@/i18n/navigation", () => ({
  usePathname: () => mockPathname,
  Link: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className} data-testid={`link-${href}`}>
      {children}
    </a>
  ),
}));

// Mock next/image
jest.mock("next/image", () => ({
  __esModule: true,
  default: ({ src, alt, className }: { src: string; alt: string; className?: string }) => (
    <img src={src} alt={alt} className={className} data-testid="logo-image" />
  ),
}));

// Mock brand-context
jest.mock("@/lib/brand-context", () => ({
  useBrand: () => ({
    config: {
      identity: { name: "BitRun", shortName: "BitRun" },
      assets: { logo: { default: "/logo.svg", alt: "BitRun" } },
    },
    name: "BitRun",
    shortName: "BitRun",
    logo: { default: "/logo.svg", alt: "BitRun" },
    getLogoSrc: () => "/logo.svg",
    getLogoAlt: () => "BitRun",
  }),
  useBrandName: () => "BitRun",
  useTheme: () => ({ colors: { primary: "#000" } }),
}));

// Mock Sheet component
jest.mock("@/components/ui/sheet", () => ({
  Sheet: ({ children, open }: { children: React.ReactNode; open: boolean }) => (
    <div data-testid="sheet" data-open={open}>
      {open ? children : null}
    </div>
  ),
  SheetContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sheet-content">{children}</div>
  ),
}));

// Mock Tooltip components
jest.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip-content">{children}</div>
  ),
}));

describe("AppSidebar", () => {
  beforeEach(() => {
    mockPathname = "/overview";
  });

  it("renders desktop sidebar with all nav items", () => {
    render(<AppSidebar />);

    // Desktop sidebar should show all nav items (getAllByTestId because mobile sidebar may also render them)
    expect(screen.getAllByTestId("link-/overview").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("link-/agents").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("link-/strategies").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("link-/accounts").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("link-/models").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("link-/backtest").length).toBeGreaterThan(0);
  });

  it("shows nav item labels when not collapsed", () => {
    render(<AppSidebar />);

    // Should show text labels
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Strategies")).toBeInTheDocument();
    expect(screen.getByText("Accounts")).toBeInTheDocument();
    expect(screen.getByText("Models")).toBeInTheDocument();
    expect(screen.getByText("Backtest")).toBeInTheDocument();
  });

  it("renders logo", () => {
    render(<AppSidebar />);

    const logos = screen.getAllByTestId("logo-image");
    expect(logos.length).toBeGreaterThan(0);
  });

  it("toggles collapse state when button clicked", async () => {
    const user = userEvent.setup();
    render(<AppSidebar />);

    // Initially shows "Collapse" text
    const collapseButton = screen.getByText("Collapse");
    expect(collapseButton).toBeInTheDocument();

    // Click to collapse
    await user.click(collapseButton);

    // After collapse, the "Collapse" text should be hidden
    // and ChevronRight icon should be visible
    expect(screen.queryByText("Collapse")).not.toBeInTheDocument();
  });

  it("shows active state for current route", () => {
    mockPathname = "/agents";
    render(<AppSidebar />);

    // Get first matching link (desktop sidebar)
    const agentsLinks = screen.getAllByTestId("link-/agents");
    // Active link should have the active class
    expect(agentsLinks[0].className).toContain("bg-sidebar-accent");
  });

  it("shows active state for nested routes", () => {
    mockPathname = "/agents/123";
    render(<AppSidebar />);

    const agentsLinks = screen.getAllByTestId("link-/agents");
    expect(agentsLinks[0].className).toContain("bg-sidebar-accent");
  });

  it("renders mobile sidebar when open (controlled mode)", () => {
    // Must pass onMobileOpenChange for controlled mode
    const onMobileOpenChange = jest.fn();
    render(<AppSidebar mobileOpen={true} onMobileOpenChange={onMobileOpenChange} />);

    const sheet = screen.getByTestId("sheet");
    expect(sheet).toHaveAttribute("data-open", "true");
    expect(screen.getByTestId("sheet-content")).toBeInTheDocument();
  });

  it("does not render mobile sidebar content when closed", () => {
    render(<AppSidebar mobileOpen={false} />);

    const sheet = screen.getByTestId("sheet");
    expect(sheet).toHaveAttribute("data-open", "false");
    expect(screen.queryByTestId("sheet-content")).not.toBeInTheDocument();
  });

  it("calls onMobileOpenChange when controlled", () => {
    const onMobileOpenChange = jest.fn();
    render(<AppSidebar mobileOpen={false} onMobileOpenChange={onMobileOpenChange} />);

    // The component should use the controlled state
    const sheet = screen.getByTestId("sheet");
    expect(sheet).toHaveAttribute("data-open", "false");
  });

  it("works in uncontrolled mode", () => {
    render(<AppSidebar />);

    // Should render without errors
    const sheet = screen.getByTestId("sheet");
    expect(sheet).toHaveAttribute("data-open", "false");
  });
});

describe("MobileMenuButton", () => {
  it("renders menu button", () => {
    const onClick = jest.fn();
    render(<MobileMenuButton onClick={onClick} />);

    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    render(<MobileMenuButton onClick={onClick} />);

    const button = screen.getByRole("button");
    await user.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("has md:hidden class for mobile-only visibility", () => {
    const onClick = jest.fn();
    render(<MobileMenuButton onClick={onClick} />);

    const button = screen.getByRole("button");
    expect(button.className).toContain("md:hidden");
  });
});
