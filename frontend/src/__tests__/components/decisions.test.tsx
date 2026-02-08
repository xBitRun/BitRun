/**
 * Tests for Decision components:
 * - AccountSnapshotSection
 * - MarketSnapshotSection
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import {
  AccountSnapshotSection,
  MarketSnapshotSection,
} from "@/components/decisions/snapshot-sections";

// Translation mock function (component receives t as prop)
const t = (key: string) => key;

// ==================== AccountSnapshotSection ====================

describe("AccountSnapshotSection", () => {
  const mockAccountSnapshot = {
    equity: 10000,
    available_balance: 7500,
    total_margin_used: 2500,
    unrealized_pnl: 150.5,
    margin_usage_percent: 25,
    position_count: 2,
    positions: [
      {
        symbol: "BTCUSDT",
        side: "long" as const,
        size: 0.1,
        size_usd: 5000,
        entry_price: 50000,
        mark_price: 51000,
        leverage: 10,
        unrealized_pnl: 100,
        unrealized_pnl_percent: 2,
        liquidation_price: 45000,
      },
    ],
  };

  it("should render the collapsible trigger with title", () => {
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    expect(
      screen.getByText("decisions.accountSnapshot.title")
    ).toBeInTheDocument();
  });

  it("should display equity in the trigger badge", () => {
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    expect(screen.getByText("$10,000.00")).toBeInTheDocument();
  });

  it("should show account details when expanded", async () => {
    const user = userEvent.setup();
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    // Click to expand
    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    // Should display account stats
    expect(
      screen.getByText("decisions.accountSnapshot.equity")
    ).toBeInTheDocument();
    expect(
      screen.getByText("decisions.accountSnapshot.availableBalance")
    ).toBeInTheDocument();
  });

  it("should show positions when expanded", async () => {
    const user = userEvent.setup();
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("LONG")).toBeInTheDocument();
  });

  it("should show no positions message when empty", async () => {
    const user = userEvent.setup();
    const emptySnapshot = { ...mockAccountSnapshot, positions: [] };
    render(<AccountSnapshotSection snapshot={emptySnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(
      screen.getByText("decisions.accountSnapshot.noPositions")
    ).toBeInTheDocument();
  });
});

// ==================== MarketSnapshotSection ====================

describe("MarketSnapshotSection", () => {
  const mockMarketSnapshot = [
    {
      symbol: "BTCUSDT",
      exchange_name: "binance",
      current: {
        mid_price: 50000,
        bid_price: 49990,
        ask_price: 50010,
        volume_24h: 1000000000,
        funding_rate: 0.0001,
      },
      indicators: {},
      klines: {},
      funding_history: [],
    },
  ];

  it("should render the collapsible trigger with symbol count", () => {
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    expect(
      screen.getByText("decisions.marketSnapshot.title")
    ).toBeInTheDocument();
    expect(screen.getByText(/1/)).toBeInTheDocument();
  });
});
