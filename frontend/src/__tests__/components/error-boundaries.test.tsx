/**
 * Tests for error boundary components: PageErrorBoundary, SectionErrorBoundary
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";


import {
  PageErrorFallback,
} from "@/components/error-boundary/page-error-boundary";
import {
  SectionErrorFallback,
  SectionErrorBoundary,
} from "@/components/error-boundary/section-error-boundary";

// ---- PageErrorFallback ----

describe("PageErrorFallback", () => {
  it("should render error title and description", () => {
    render(<PageErrorFallback />);

    expect(screen.getByText("Page Error")).toBeInTheDocument();
    expect(
      screen.getByText(/We encountered an error while loading this page/)
    ).toBeInTheDocument();
  });

  it("should render Go Back and Home buttons", () => {
    render(<PageErrorFallback />);

    expect(screen.getByText("Go Back")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
  });

  it("should render Try Again button when reset is provided", () => {
    render(<PageErrorFallback reset={jest.fn()} />);

    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("should call reset when Try Again is clicked", async () => {
    const user = userEvent.setup();
    const handleReset = jest.fn();

    render(<PageErrorFallback reset={handleReset} />);

    await user.click(screen.getByText("Try Again"));

    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});

// ---- SectionErrorFallback ----

describe("SectionErrorFallback", () => {
  it("should render default title and message", () => {
    render(<SectionErrorFallback />);

    expect(screen.getByText("Error loading section")).toBeInTheDocument();
    expect(
      screen.getByText("This section couldn't be loaded. Please try again.")
    ).toBeInTheDocument();
  });

  it("should render custom title and message", () => {
    render(
      <SectionErrorFallback
        title="Chart Error"
        message="Could not load chart data"
      />
    );

    expect(screen.getByText("Chart Error")).toBeInTheDocument();
    expect(screen.getByText("Could not load chart data")).toBeInTheDocument();
  });

  it("should render Retry button when onRetry is provided", () => {
    render(<SectionErrorFallback onRetry={jest.fn()} />);

    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("should render compact mode", () => {
    const { container } = render(
      <SectionErrorFallback compact={true} message="Compact error message" />
    );

    expect(screen.getByText("Compact error message")).toBeInTheDocument();
    // Compact mode uses flex items-center layout
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass("flex", "items-center");
  });
});

// ---- SectionErrorBoundary ----

describe("SectionErrorBoundary", () => {
  // Suppress error boundary console output during these tests
  const originalConsoleError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });
  afterAll(() => {
    console.error = originalConsoleError;
  });

  const ThrowingComponent = () => {
    throw new Error("Test render error");
  };

  it("should render children when no error occurs", () => {
    render(
      <SectionErrorBoundary>
        <div>Normal Content</div>
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Normal Content")).toBeInTheDocument();
  });

  it("should render fallback when a child throws an error", () => {
    render(
      <SectionErrorBoundary>
        <ThrowingComponent />
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Error loading section")).toBeInTheDocument();
  });
});
