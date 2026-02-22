/**
 * Tests for SymbolSelector component
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { SymbolSelector } from "@/components/symbol-selector/symbol-selector";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "single.placeholder": "Select symbol",
      "multiple.placeholder": "Select symbols",
      searchPlaceholder: "Search...",
      loading: "Loading...",
      loadFailed: "Failed to load",
      retry: "Retry",
      noResults: "No results",
      customPlaceholder: "Custom symbol",
      "marketType.crypto": "Crypto",
      "marketType.forex": "Forex",
      "marketType.metals": "Metals",
    };
    return translations[key] || key;
  },
}));

// Mock useSymbolsList
jest.mock("@/hooks/use-symbols", () => ({
  useSymbolsList: jest.fn(() => ({
    symbols: [],
    isLoading: false,
    error: null,
  })),
}));

// Mock useSettlementCurrency
jest.mock("@/hooks/use-exchange-capabilities", () => ({
  useSettlementCurrency: jest.fn(() => ({
    settlement: "USDT",
    isLoading: false,
  })),
}));

// Mock symbol-selector constants
jest.mock("@/components/symbol-selector/constants", () => ({
  POPULAR_CRYPTO_SYMBOLS: ["BTC", "ETH", "SOL"],
  FOREX_SYMBOLS: ["EURUSD", "GBPUSD"],
  METALS_SYMBOLS: ["XAUUSD", "XAGUSD"],
  extractBaseSymbol: (s: string) => s.split("/")[0],
  detectMarketType: () => "crypto_perp",
}));

const mockOnChange = jest.fn();

describe("SymbolSelector", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("renders with placeholder when no value", () => {
      render(<SymbolSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByText("Select symbols")).toBeInTheDocument();
    });

    it("renders with placeholder for null value", () => {
      render(<SymbolSelector value={null as unknown as string[]} onChange={mockOnChange} />);

      expect(screen.getByText("Select symbols")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          className="custom-selector"
        />
      );

      expect(document.querySelector(".custom-selector")).toBeInTheDocument();
    });
  });

  describe("single mode", () => {
    it("renders with single placeholder", () => {
      render(
        <SymbolSelector value="" onChange={mockOnChange} mode="single" />
      );

      expect(screen.getByText("Select symbol")).toBeInTheDocument();
    });

    it("renders empty string value", () => {
      render(
        <SymbolSelector value="" onChange={mockOnChange} mode="single" />
      );

      expect(screen.getByText("Select symbol")).toBeInTheDocument();
    });
  });

  describe("disabled state", () => {
    it("disables the trigger button when disabled", () => {
      render(<SymbolSelector value={[]} onChange={mockOnChange} disabled />);

      const button = screen.getByRole("combobox");
      expect(button).toBeDisabled();
    });

    it("enables the trigger button by default", () => {
      render(<SymbolSelector value={[]} onChange={mockOnChange} />);

      const button = screen.getByRole("combobox");
      expect(button).not.toBeDisabled();
    });
  });

  describe("size variants", () => {
    it("applies sm size class", () => {
      render(
        <SymbolSelector value={[]} onChange={mockOnChange} size="sm" />
      );

      const button = screen.getByRole("combobox");
      expect(button).toHaveClass("h-8");
    });

    it("applies md size class by default", () => {
      render(
        <SymbolSelector value={[]} onChange={mockOnChange} />
      );

      const button = screen.getByRole("combobox");
      expect(button).toHaveClass("h-10");
    });

    it("applies lg size class", () => {
      render(
        <SymbolSelector value={[]} onChange={mockOnChange} size="lg" />
      );

      const button = screen.getByRole("combobox");
      expect(button).toHaveClass("h-12");
    });
  });

  describe("custom placeholder", () => {
    it("uses custom placeholder when provided", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          placeholder="Choose a pair"
        />
      );

      expect(screen.getByText("Choose a pair")).toBeInTheDocument();
    });
  });

  describe("combobox role", () => {
    it("has combobox role", () => {
      render(<SymbolSelector value={[]} onChange={mockOnChange} />);

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("has aria-expanded attribute", () => {
      render(<SymbolSelector value={[]} onChange={mockOnChange} />);

      const combobox = screen.getByRole("combobox");
      expect(combobox).toHaveAttribute("aria-expanded");
    });
  });

  describe("props handling", () => {
    it("accepts exchange prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          exchange="binance"
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("accepts assetType prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          assetType="crypto_spot"
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("accepts maxSelections prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          maxSelections={5}
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("accepts showMarketTypeTabs prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          showMarketTypeTabs={false}
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("accepts allowCustomInput prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          allowCustomInput={false}
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("accepts showPopularSymbols prop", () => {
      render(
        <SymbolSelector
          value={[]}
          onChange={mockOnChange}
          showPopularSymbols={true}
        />
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });
  });
});
