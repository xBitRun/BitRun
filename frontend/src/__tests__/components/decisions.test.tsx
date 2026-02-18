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

  it("should display negative unrealized P&L correctly", async () => {
    const user = userEvent.setup();
    const negativePnlSnapshot = {
      ...mockAccountSnapshot,
      unrealized_pnl: -50.25,
    };
    render(<AccountSnapshotSection snapshot={negativePnlSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText(/-50\.25/)).toBeInTheDocument();
  });

  it("should display position with short side", async () => {
    const user = userEvent.setup();
    const shortPositionSnapshot = {
      ...mockAccountSnapshot,
      positions: [
        {
          ...mockAccountSnapshot.positions[0],
          side: "short" as const,
        },
      ],
    };
    render(<AccountSnapshotSection snapshot={shortPositionSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText("SHORT")).toBeInTheDocument();
  });

  it("should display position details correctly", async () => {
    const user = userEvent.setup();
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText("decisions.accountSnapshot.sizeValue")).toBeInTheDocument();
    expect(screen.getByText("decisions.accountSnapshot.sizeQty")).toBeInTheDocument();
    expect(screen.getByText("decisions.accountSnapshot.entry")).toBeInTheDocument();
    expect(screen.getByText("decisions.accountSnapshot.leverage")).toBeInTheDocument();
    expect(screen.getByText("decisions.accountSnapshot.liquidation")).toBeInTheDocument();
  });

  it("should handle position with null liquidation price", async () => {
    const user = userEvent.setup();
    const snapshotWithNullLiquidation = {
      ...mockAccountSnapshot,
      positions: [
        {
          ...mockAccountSnapshot.positions[0],
          liquidation_price: null,
        },
      ],
    };
    render(<AccountSnapshotSection snapshot={snapshotWithNullLiquidation} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("should toggle collapse/expand", async () => {
    const user = userEvent.setup();
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    const trigger = screen.getByText("decisions.accountSnapshot.title");

    // Expand
    await user.click(trigger);
    expect(screen.getByText("decisions.accountSnapshot.equity")).toBeInTheDocument();

    // Collapse
    await user.click(trigger);
    expect(screen.queryByText("decisions.accountSnapshot.equity")).not.toBeInTheDocument();
  });

  it("should display margin usage percentage", async () => {
    const user = userEvent.setup();
    render(<AccountSnapshotSection snapshot={mockAccountSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText(/25\.0%/)).toBeInTheDocument();
  });

  it("should display multiple positions", async () => {
    const user = userEvent.setup();
    const multiplePositionsSnapshot = {
      ...mockAccountSnapshot,
      positions: [
        mockAccountSnapshot.positions[0],
        {
          ...mockAccountSnapshot.positions[0],
          symbol: "ETHUSDT",
          side: "short" as const,
        },
      ],
    };
    render(<AccountSnapshotSection snapshot={multiplePositionsSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.accountSnapshot.title")
    );

    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("ETHUSDT")).toBeInTheDocument();
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
      available_timeframes: ["1h", "4h", "1d"],
    },
  ];

  it("should render the collapsible trigger with symbol count", () => {
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    expect(
      screen.getByText("decisions.marketSnapshot.title")
    ).toBeInTheDocument();
    expect(screen.getByText(/1/)).toBeInTheDocument();
  });

  it("should expand when clicked", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
  });

  it("should display price details when expanded", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("decisions.marketSnapshot.bid")).toBeInTheDocument();
    expect(screen.getByText("decisions.marketSnapshot.ask")).toBeInTheDocument();
    expect(screen.getByText("decisions.marketSnapshot.spread")).toBeInTheDocument();
  });

  it("should calculate and display spread percentage", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    // Spread = (50010 - 49990) / 50000 * 100 = 0.04%
    expect(screen.getByText(/0\.040%/)).toBeInTheDocument();
  });

  it("should display funding rate when available", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    // 0.0001 * 100 = 0.0100%
    expect(screen.getByText(/0\.0100%/)).toBeInTheDocument();
  });

  it("should display N/A when funding rate is null", async () => {
    const user = userEvent.setup();
    const snapshotWithoutFunding = [
      {
        ...mockMarketSnapshot[0],
        current: {
          ...mockMarketSnapshot[0].current,
          funding_rate: null,
        },
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithoutFunding} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("should display indicators when available", async () => {
    const user = userEvent.setup();
    const snapshotWithIndicators = [
      {
        ...mockMarketSnapshot[0],
        indicators: {
          "1h": {
            ema_trend: "bullish",
            rsi: 65.5,
            rsi_signal: "bullish",
            macd: {
              macd: 0.5,
              signal: 0.3,
              histogram: 0.2,
            },
            macd_signal: "bullish",
            atr: 500,
            ema: {
              "9": 49900,
            },
            bollinger: {
              upper: 51000,
              middle: 50000,
              lower: 49000,
            },
          },
        },
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithIndicators} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("decisions.marketSnapshot.indicators")).toBeInTheDocument();
  });

  it("should display klines table when available", async () => {
    const user = userEvent.setup();
    const snapshotWithKlines = [
      {
        ...mockMarketSnapshot[0],
        klines: {
          "1h": [
            {
              timestamp: "2024-01-01T00:00:00Z",
              open: 50000,
              high: 51000,
              low: 49000,
              close: 50500,
              volume: 1000,
            },
          ],
        },
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithKlines} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText(/decisions\.marketSnapshot\.recentKlines/)).toBeInTheDocument();
    expect(screen.getByText("decisions.marketSnapshot.time")).toBeInTheDocument();
  });

  it("should display funding history when available", async () => {
    const user = userEvent.setup();
    const snapshotWithFunding = [
      {
        ...mockMarketSnapshot[0],
        funding_history: [
          {
            timestamp: "2024-01-01T00:00:00Z",
            rate: 0.0001,
          },
        ],
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithFunding} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("decisions.marketSnapshot.fundingHistory")).toBeInTheDocument();
  });

  it("should handle multiple symbols", async () => {
    const user = userEvent.setup();
    const multipleSymbols = [
      mockMarketSnapshot[0],
      { ...mockMarketSnapshot[0], symbol: "ETHUSDT" },
    ];
    render(<MarketSnapshotSection snapshot={multipleSymbols} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("ETHUSDT")).toBeInTheDocument();
  });

  it("should display exchange name badge when available", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    expect(screen.getByText("binance")).toBeInTheDocument();
  });

  it("should handle zero mid_price for spread calculation", async () => {
    const user = userEvent.setup();
    const snapshotWithZeroPrice = [
      {
        ...mockMarketSnapshot[0],
        current: {
          ...mockMarketSnapshot[0].current,
          mid_price: 0,
        },
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithZeroPrice} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    // Should display 0.000% for spread
    expect(screen.getByText(/0\.000%/)).toBeInTheDocument();
  });

  it("should calculate average funding rate from history", async () => {
    const user = userEvent.setup();
    const snapshotWithFundingHistory = [
      {
        ...mockMarketSnapshot[0],
        funding_history: [
          { timestamp: "2024-01-01T00:00:00Z", rate: 0.0001 },
          { timestamp: "2024-01-01T08:00:00Z", rate: 0.0002 },
          { timestamp: "2024-01-01T16:00:00Z", rate: 0.0003 },
        ],
      },
    ];
    render(<MarketSnapshotSection snapshot={snapshotWithFundingHistory} t={t} />);

    await user.click(
      screen.getByText("decisions.marketSnapshot.title")
    );

    // Avg = (0.0001 + 0.0002 + 0.0003) / 3 = 0.0002 = 0.0200%
    const avgFundingElements = screen.getAllByText(/0\.0200%/);
    expect(avgFundingElements.length).toBeGreaterThanOrEqual(1);
  });

  it("should toggle collapse/expand", async () => {
    const user = userEvent.setup();
    render(<MarketSnapshotSection snapshot={mockMarketSnapshot} t={t} />);

    const trigger = screen.getByText("decisions.marketSnapshot.title");

    // Expand
    await user.click(trigger);
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();

    // Collapse
    await user.click(trigger);
    expect(screen.queryByText("BTCUSDT")).not.toBeInTheDocument();
  });
});
