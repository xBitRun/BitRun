/**
 * Test Utilities
 *
 * Custom render functions and utilities for testing React components.
 */

import React, { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { ThemeProvider } from "next-themes";

// Mock providers
const MockProviders = ({ children }: { children: React.ReactNode }) => {
  return (
    <ThemeProvider attribute="class" defaultTheme="light">
      {children}
    </ThemeProvider>
  );
};

// Custom render function that includes all providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">
) => render(ui, { wrapper: MockProviders, ...options });

// Re-export everything
export * from "@testing-library/react";
export { customRender as render };

// Helper to create mock API responses
export const createMockApiResponse = <T,>(data: T, status = 200) => {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
};

// Helper to mock fetch for API calls
export const mockFetch = <T,>(
  data: T,
  options: { status?: number; delay?: number } = {}
) => {
  const { status = 200, delay = 0 } = options;

  return jest.fn().mockImplementation(async () => {
    if (delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    return createMockApiResponse(data, status);
  });
};

// Helper to wait for loading states
export const waitForLoadingToFinish = async () => {
  await new Promise((resolve) => setTimeout(resolve, 0));
};

// Mock user data
export const mockUser = {
  id: "test-user-id",
  email: "test@example.com",
  name: "Test User",
};

// Mock strategy data
export const mockStrategy = {
  id: "test-strategy-id",
  name: "Test Strategy",
  prompt: "Test prompt",
  status: "active",
  config: {
    execution_interval_minutes: 30,
    max_positions: 3,
    symbols: ["BTC", "ETH"],
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// Mock account data
export const mockAccount = {
  id: "test-account-id",
  name: "Test Account",
  exchange: "binance",
  is_testnet: true,
  connection_status: "connected",
  created_at: new Date().toISOString(),
};

// Mock decision data
export const mockDecision = {
  id: "test-decision-id",
  strategy_id: "test-strategy-id",
  action: "open_long",
  symbol: "BTC",
  confidence: 75,
  reasoning: "Strong bullish momentum",
  created_at: new Date().toISOString(),
};
