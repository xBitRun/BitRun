/**
 * Tests for TradeHistoryTable component
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { TradeHistoryTable } from "@/components/analytics/trade-history-table";
import type { PnLTradeRecord } from "@/lib/api/endpoints";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    const translations: Record<string, string> = {
      "columns.symbol": "Symbol",
      "columns.side": "Side",
      "columns.entry": "Entry",
      "columns.exit": "Exit",
      "columns.size": "Size",
      "columns.pnl": "P&L",
      "columns.duration": "Duration",
      "columns.exitReason": "Exit",
      "columns.time": "Time",
      noData: "No trades found",
      pagination: `Showing ${params?.current} of ${params?.pages} pages (${params?.total} total)`,
    };
    return translations[key] || key;
  },
}));

const mockTrades: PnLTradeRecord[] = [
  {
    id: "trade-1",
    symbol: "BTC/USDT",
    side: "long",
    entry_price: 50000.0,
    exit_price: 52000.0,
    size_usd: 1000.0,
    realized_pnl: 100.0,
    duration_minutes: 120,
    exit_reason: "take_profit",
    closed_at: "2024-01-01T12:00:00Z",
  },
  {
    id: "trade-2",
    symbol: "ETH/USDT",
    side: "short",
    entry_price: 3000.0,
    exit_price: 2900.0,
    size_usd: 500.0,
    realized_pnl: -50.0,
    duration_minutes: 60,
    exit_reason: "stop_loss",
    closed_at: "2024-01-02T14:30:00Z",
  },
  {
    id: "trade-3",
    symbol: "SOL/USDT",
    side: "long",
    entry_price: 100.0,
    exit_price: null,
    size_usd: 200.0,
    realized_pnl: 0,
    duration_minutes: 30,
    exit_reason: null,
    closed_at: "2024-01-03T09:00:00Z",
  },
];

describe("TradeHistoryTable", () => {
  const defaultProps = {
    trades: mockTrades,
    total: 30,
    limit: 10,
    offset: 0,
    onPageChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading skeleton when isLoading is true", () => {
    render(<TradeHistoryTable {...defaultProps} isLoading />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no trades", () => {
    render(<TradeHistoryTable {...defaultProps} trades={[]} />);

    expect(screen.getByText("No trades found")).toBeInTheDocument();
  });

  it("renders trade rows", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByText("ETH/USDT")).toBeInTheDocument();
    expect(screen.getByText("SOL/USDT")).toBeInTheDocument();
  });

  it("displays correct side badges", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    // Two longs and one short
    const longs = screen.getAllByText("long");
    expect(longs.length).toBe(2);
    expect(screen.getByText("short")).toBeInTheDocument();
  });

  it("formats currency correctly for profits", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText(/\+\$100\.00/)).toBeInTheDocument();
  });

  it("formats currency correctly for losses", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText(/-\$50\.00/)).toBeInTheDocument();
  });

  it("displays exit reason badges", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText("TP")).toBeInTheDocument();
    expect(screen.getByText("SL")).toBeInTheDocument();
  });

  it("shows dash when exit price is null", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    const cells = screen.getAllByText("-");
    expect(cells.length).toBeGreaterThan(0);
  });

  it("formats duration correctly", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    // 120 minutes = 2h
    expect(screen.getByText("2h")).toBeInTheDocument();
    // 60 minutes = 1h
    expect(screen.getByText("1h")).toBeInTheDocument();
    // 30 minutes
    expect(screen.getByText("30m")).toBeInTheDocument();
  });

  it("shows pagination when multiple pages", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText(/Showing 1 of 3 pages/)).toBeInTheDocument();
  });

  it("does not show pagination when single page", () => {
    render(<TradeHistoryTable {...defaultProps} total={5} />);

    expect(screen.queryByText(/Showing/)).not.toBeInTheDocument();
  });

  it("disables previous button on first page", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    const buttons = screen.getAllByRole("button");
    const prevButton = buttons[0];
    expect(prevButton).toBeDisabled();
  });

  it("enables previous button on later pages", () => {
    render(<TradeHistoryTable {...defaultProps} offset={10} />);

    const buttons = screen.getAllByRole("button");
    const prevButton = buttons[0];
    expect(prevButton).not.toBeDisabled();
  });

  it("calls onPageChange with correct offset when next clicked", () => {
    const onPageChange = jest.fn();
    render(<TradeHistoryTable {...defaultProps} onPageChange={onPageChange} />);

    const buttons = screen.getAllByRole("button");
    const nextButton = buttons[1];
    fireEvent.click(nextButton);

    expect(onPageChange).toHaveBeenCalledWith(10);
  });

  it("calls onPageChange with correct offset when prev clicked", () => {
    const onPageChange = jest.fn();
    render(
      <TradeHistoryTable {...defaultProps} offset={10} onPageChange={onPageChange} />
    );

    const buttons = screen.getAllByRole("button");
    const prevButton = buttons[0];
    fireEvent.click(prevButton);

    expect(onPageChange).toHaveBeenCalledWith(0);
  });

  it("applies custom className", () => {
    render(<TradeHistoryTable {...defaultProps} className="custom-table" />);

    const container = document.querySelector(".custom-table");
    expect(container).toBeInTheDocument();
  });

  it("renders column headers", () => {
    render(<TradeHistoryTable {...defaultProps} />);

    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Side")).toBeInTheDocument();
    expect(screen.getByText("Entry")).toBeInTheDocument();
    expect(screen.getByText("Size")).toBeInTheDocument();
    expect(screen.getByText("P&L")).toBeInTheDocument();
    expect(screen.getByText("Duration")).toBeInTheDocument();
    expect(screen.getByText("Time")).toBeInTheDocument();
  });
});
