/**
 * Tests for DashboardLayoutClient component.
 * Covers sidebar integration, header rendering, and mobile menu state.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { DashboardLayoutClient } from "@/app/[locale]/(dashboard)/layout-client";

// Mock child components
jest.mock("@/components/layout/header", () => ({
  Header: ({ onMenuClick }: { onMenuClick: () => void }) => (
    <header data-testid="header">
      <button data-testid="menu-button" onClick={onMenuClick}>
        Menu
      </button>
    </header>
  ),
}));

jest.mock("@/components/layout/app-sidebar", () => ({
  AppSidebar: ({
    mobileOpen,
    onMobileOpenChange,
  }: {
    mobileOpen: boolean;
    onMobileOpenChange: (open: boolean) => void;
  }) => (
    <aside data-testid="sidebar" data-mobile-open={mobileOpen}>
      <button
        data-testid="close-mobile-sidebar"
        onClick={() => onMobileOpenChange(false)}
      >
        Close
      </button>
    </aside>
  ),
}));

jest.mock("@/components/onboarding", () => ({
  FloatingSetupGuide: () => <div data-testid="floating-setup-guide" />,
}));

describe("DashboardLayoutClient", () => {
  it("renders all layout components", () => {
    render(
      <DashboardLayoutClient>
        <div>Page Content</div>
      </DashboardLayoutClient>
    );

    expect(screen.getByTestId("header")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("floating-setup-guide")).toBeInTheDocument();
  });

  it("renders children in main content area", () => {
    render(
      <DashboardLayoutClient>
        <div data-testid="page-content">Page Content</div>
      </DashboardLayoutClient>
    );

    expect(screen.getByTestId("page-content")).toBeInTheDocument();
    expect(screen.getByText("Page Content")).toBeInTheDocument();
  });

  it("initializes with mobile menu closed", () => {
    render(
      <DashboardLayoutClient>
        <div>Content</div>
      </DashboardLayoutClient>
    );

    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "false");
  });

  it("opens mobile menu when header menu button is clicked", () => {
    render(
      <DashboardLayoutClient>
        <div>Content</div>
      </DashboardLayoutClient>
    );

    const menuButton = screen.getByTestId("menu-button");
    fireEvent.click(menuButton);

    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "true");
  });

  it("closes mobile menu via sidebar callback", () => {
    render(
      <DashboardLayoutClient>
        <div>Content</div>
      </DashboardLayoutClient>
    );

    // First open the menu
    const menuButton = screen.getByTestId("menu-button");
    fireEvent.click(menuButton);

    // Verify it's open
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "true");

    // Close via sidebar's close button
    const closeButton = screen.getByTestId("close-mobile-sidebar");
    fireEvent.click(closeButton);

    expect(sidebar).toHaveAttribute("data-mobile-open", "false");
  });

  it("has correct layout structure", () => {
    const { container } = render(
      <DashboardLayoutClient>
        <div>Content</div>
      </DashboardLayoutClient>
    );

    // Check for flex container
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv.className).toContain("flex");
    expect(outerDiv.className).toContain("h-screen");
    expect(outerDiv.className).toContain("overflow-hidden");
  });

  it("main content area has scrollable overflow", () => {
    const { container } = render(
      <DashboardLayoutClient>
        <div>Content</div>
      </DashboardLayoutClient>
    );

    const main = container.querySelector("main");
    expect(main).toBeInTheDocument();
    expect(main?.className).toContain("overflow-y-auto");
    expect(main?.className).toContain("flex-1");
  });

  it("renders multiple children correctly", () => {
    render(
      <DashboardLayoutClient>
        <div data-testid="child-1">Child 1</div>
        <div data-testid="child-2">Child 2</div>
        <div data-testid="child-3">Child 3</div>
      </DashboardLayoutClient>
    );

    expect(screen.getByTestId("child-1")).toBeInTheDocument();
    expect(screen.getByTestId("child-2")).toBeInTheDocument();
    expect(screen.getByTestId("child-3")).toBeInTheDocument();
  });

  it("preserves mobile menu state across re-renders", () => {
    const { rerender } = render(
      <DashboardLayoutClient>
        <div>Content 1</div>
      </DashboardLayoutClient>
    );

    // Open the menu
    const menuButton = screen.getByTestId("menu-button");
    fireEvent.click(menuButton);

    // Re-render with different children
    rerender(
      <DashboardLayoutClient>
        <div>Content 2</div>
      </DashboardLayoutClient>
    );

    // Menu should still be open after re-render
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "true");
  });
});
