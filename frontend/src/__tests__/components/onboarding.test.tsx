/**
 * Tests for Onboarding components:
 * - FloatingSetupGuide
 * - InlineOnboardingWizard
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock next/link
jest.mock("next/link", () => ({
  __esModule: true,
  default: ({
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

// Mock hooks used by FloatingSetupGuide
const mockAccounts: unknown[] = [];
const mockStrategies: unknown[] = [];
const mockModels: unknown[] = [];

jest.mock("@/hooks", () => ({
  useAccounts: () => ({
    accounts: mockAccounts,
    isLoading: false,
  }),
  useStrategies: () => ({
    strategies: mockStrategies,
    isLoading: false,
  }),
  useModels: () => ({
    models: mockModels,
    isLoading: false,
  }),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock API modules used by InlineOnboardingWizard
jest.mock("@/lib/api", () => ({
  accountsApi: {
    create: jest.fn().mockResolvedValue({ id: "test-account-id" }),
  },
  strategiesApi: {
    create: jest.fn().mockResolvedValue({ id: "test-strategy-id" }),
  },
  authApi: {},
}));

import { FloatingSetupGuide } from "@/components/onboarding/floating-setup-guide";
import { InlineOnboardingWizard } from "@/components/onboarding/inline-wizard";

// ==================== FloatingSetupGuide ====================

describe("FloatingSetupGuide", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    // Reset mock arrays
    mockAccounts.length = 0;
    mockStrategies.length = 0;
    mockModels.length = 0;
  });

  it("should render guide when not dismissed and steps incomplete", () => {
    render(<FloatingSetupGuide />);

    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("subtitle")).toBeInTheDocument();
  });

  it("should render step items", () => {
    render(<FloatingSetupGuide />);

    expect(screen.getByText("steps.account.title")).toBeInTheDocument();
    expect(screen.getByText("steps.agent.title")).toBeInTheDocument();
    expect(screen.getByText("steps.models.title")).toBeInTheDocument();
  });

  it("should show progress indicator", () => {
    render(<FloatingSetupGuide />);

    expect(screen.getByText("0/3")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("should dismiss when X button is clicked", async () => {
    const user = userEvent.setup();
    render(<FloatingSetupGuide />);

    // Find dismiss button - it's a small icon button with the X svg
    const buttons = screen.getAllByRole("button");
    // The dismiss button contains a lucide-x SVG; look for it via the svg class
    const dismissBtn = buttons.find((b) =>
      b.querySelector('[class*="lucide-x"]')
    );

    expect(dismissBtn).toBeTruthy();
    if (dismissBtn) {
      await user.click(dismissBtn);
    }

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "bitrun-setup-guide-dismissed",
      "true"
    );
  });

  it("should not render when all required steps are complete", () => {
    // Add items to make all 3 steps complete (account, models, agent)
    mockAccounts.push({ id: "1" });
    mockModels.push({ id: "1" });
    mockStrategies.push({ id: "1" });

    const { container } = render(<FloatingSetupGuide />);

    // Should return null (empty container)
    expect(container.innerHTML).toBe("");
  });

  it("should not render when dismissed from localStorage", () => {
    localStorageMock.getItem.mockReturnValue("true");

    const { container } = render(<FloatingSetupGuide />);

    expect(container.innerHTML).toBe("");
  });
});

// ==================== InlineOnboardingWizard ====================

describe("InlineOnboardingWizard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render step indicator", () => {
    render(<InlineOnboardingWizard />);

    // Step labels should be visible
    expect(screen.getByText("Welcome")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.getByText("Agent")).toBeInTheDocument();
    expect(screen.getByText("Risk")).toBeInTheDocument();
    expect(screen.getByText("Launch")).toBeInTheDocument();
  });

  it("should start on welcome step", () => {
    render(<InlineOnboardingWizard />);

    expect(screen.getByText("welcome.title")).toBeInTheDocument();
    expect(screen.getByText("welcome.subtitle")).toBeInTheDocument();
  });
});
