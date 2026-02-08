/**
 * Tests for Strategy Studio components:
 * - CoinSelector
 * - RiskControlsPanel
 * - StrategyPresetSelector
 * - TimeframeSelector
 * - IndicatorConfig
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock @/types
jest.mock("@/types", () => ({
  POPULAR_SYMBOLS: ["BTC", "ETH", "SOL", "BNB", "XRP"],
  TIMEFRAME_OPTIONS: [
    { value: "1m", label: "1 minute" },
    { value: "5m", label: "5 minutes" },
    { value: "15m", label: "15 minutes" },
    { value: "30m", label: "30 minutes" },
    { value: "1h", label: "1 hour" },
    { value: "4h", label: "4 hours" },
    { value: "1d", label: "1 day" },
  ],
  getStrategyPreset: jest.fn(() => null),
}));

// Mock @/i18n/navigation
jest.mock("@/i18n/navigation", () => ({
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

import { CoinSelector } from "@/components/strategy-studio/coin-selector";
import { RiskControlsPanel } from "@/components/strategy-studio/risk-controls-panel";
import { StrategyPresetSelector } from "@/components/strategy-studio/strategy-preset-selector";
import { TimeframeSelector } from "@/components/strategy-studio/timeframe-selector";
import { IndicatorConfig } from "@/components/strategy-studio/indicator-config";
import type { RiskControlsConfig, IndicatorSettings } from "@/types";

// ==================== CoinSelector ====================

describe("CoinSelector", () => {
  const defaultProps = {
    value: [] as string[],
    onChange: jest.fn(),
    maxCoins: 10,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and description", () => {
    render(<CoinSelector {...defaultProps} />);

    expect(screen.getByText("coinSelector.title")).toBeInTheDocument();
    expect(screen.getByText("coinSelector.description")).toBeInTheDocument();
  });

  it("should show empty state when no coins selected", () => {
    render(<CoinSelector {...defaultProps} />);

    expect(
      screen.getByText("coinSelector.noCoinsSelected")
    ).toBeInTheDocument();
  });

  it("should display selected coins as badges", () => {
    render(<CoinSelector {...defaultProps} value={["BTC", "ETH"]} />);

    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("ETH")).toBeInTheDocument();
  });

  it("should call onChange when adding a popular symbol", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<CoinSelector {...defaultProps} onChange={onChange} />);

    // Click on SOL button (BTC, ETH, SOL etc are in POPULAR_SYMBOLS)
    const solButton = screen.getByRole("button", { name: /SOL/ });
    await user.click(solButton);

    expect(onChange).toHaveBeenCalledWith(["SOL"]);
  });

  it("should call onChange when removing a coin", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(
      <CoinSelector {...defaultProps} value={["BTC", "ETH"]} onChange={onChange} />
    );

    // Find the remove button inside the BTC badge
    const btcBadge = screen.getByText("BTC").closest(".px-3");
    const removeButton = btcBadge?.querySelector("button");
    if (removeButton) {
      await user.click(removeButton);
    }

    expect(onChange).toHaveBeenCalledWith(["ETH"]);
  });

  it("should show selected count", () => {
    render(<CoinSelector {...defaultProps} value={["BTC", "ETH"]} />);

    expect(screen.getByText(/2\/10/)).toBeInTheDocument();
  });

  it("should add custom coin via input", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<CoinSelector {...defaultProps} onChange={onChange} />);

    const customInput = screen.getByPlaceholderText(
      "coinSelector.customPlaceholder"
    );
    await user.type(customInput, "DOGE");
    await user.keyboard("{Enter}");

    expect(onChange).toHaveBeenCalledWith(["DOGE"]);
  });

  it("should filter popular symbols by search", async () => {
    const user = userEvent.setup();
    render(<CoinSelector {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(
      "coinSelector.searchPlaceholder"
    );
    await user.type(searchInput, "BT");

    // BTC should be visible, SOL should not
    expect(screen.getByRole("button", { name: /BTC/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /SOL/ })).not.toBeInTheDocument();
  });
});

// ==================== RiskControlsPanel ====================

describe("RiskControlsPanel", () => {
  const defaultRiskConfig: RiskControlsConfig = {
    maxLeverage: 5,
    maxPositionRatio: 0.1,
    maxTotalExposure: 0.5,
    minRiskRewardRatio: 2.0,
    maxDrawdownPercent: 0.15,
    minConfidence: 65,
  };

  const defaultProps = {
    value: defaultRiskConfig,
    onChange: jest.fn(),
    tradingMode: "conservative" as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and description", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    expect(screen.getByText("riskControls.title")).toBeInTheDocument();
    expect(screen.getByText("riskControls.description")).toBeInTheDocument();
  });

  it("should display risk level indicator", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    expect(screen.getByText("riskControls.riskLevel")).toBeInTheDocument();
  });

  it("should display current max leverage value", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    expect(screen.getByText("riskControls.maxLeverage")).toBeInTheDocument();
    // The numeric input has value 5
    const leverageInput = screen.getByDisplayValue("5");
    expect(leverageInput).toBeInTheDocument();
  });

  it("should display position ratio percentage", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    expect(screen.getByText("10%")).toBeInTheDocument();
  });

  it("should show high risk warning for aggressive settings", () => {
    const highRiskConfig: RiskControlsConfig = {
      maxLeverage: 40,
      maxPositionRatio: 0.4,
      maxTotalExposure: 0.9,
      minRiskRewardRatio: 1.0,
      maxDrawdownPercent: 0.4,
      minConfidence: 40,
    };
    render(
      <RiskControlsPanel {...defaultProps} value={highRiskConfig} />
    );

    expect(
      screen.getByText("riskControls.highRiskWarning")
    ).toBeInTheDocument();
  });
});

// ==================== StrategyPresetSelector ====================

describe("StrategyPresetSelector", () => {
  const defaultProps = {
    riskProfile: null as null,
    timeHorizon: null as null,
    isCustom: false,
    onSelect: jest.fn(),
    onCustom: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and description", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("description")).toBeInTheDocument();
  });

  it("should render risk profile options", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(
      screen.getByText("riskProfile.conservative")
    ).toBeInTheDocument();
    expect(screen.getByText("riskProfile.balanced")).toBeInTheDocument();
    expect(screen.getByText("riskProfile.aggressive")).toBeInTheDocument();
  });

  it("should render time horizon options", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(screen.getByText("timeHorizon.scalp")).toBeInTheDocument();
    expect(screen.getByText("timeHorizon.swing")).toBeInTheDocument();
    expect(screen.getByText("timeHorizon.position")).toBeInTheDocument();
  });

  it("should call onSelect when clicking a risk profile", async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(<StrategyPresetSelector {...defaultProps} onSelect={onSelect} />);

    await user.click(screen.getByText("riskProfile.conservative"));

    // Should select conservative with default swing horizon
    expect(onSelect).toHaveBeenCalledWith("conservative", "swing");
  });

  it("should call onCustom when clicking custom option", async () => {
    const user = userEvent.setup();
    const onCustom = jest.fn();
    render(<StrategyPresetSelector {...defaultProps} onCustom={onCustom} />);

    await user.click(screen.getByText("custom"));

    expect(onCustom).toHaveBeenCalled();
  });
});

// ==================== TimeframeSelector ====================

describe("TimeframeSelector", () => {
  const defaultProps = {
    value: ["1h" as const],
    onChange: jest.fn(),
    maxTimeframes: 5,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and description", () => {
    render(<TimeframeSelector {...defaultProps} />);

    expect(screen.getByText("timeframes.title")).toBeInTheDocument();
    expect(screen.getByText("timeframes.description")).toBeInTheDocument();
  });

  it("should display selected count", () => {
    render(<TimeframeSelector {...defaultProps} />);

    expect(screen.getByText(/1\/5/)).toBeInTheDocument();
  });

  it("should render all timeframe options", () => {
    render(<TimeframeSelector {...defaultProps} />);

    expect(screen.getByText("1m")).toBeInTheDocument();
    expect(screen.getByText("5m")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("1d")).toBeInTheDocument();
  });

  it("should call onChange when toggling a timeframe", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<TimeframeSelector {...defaultProps} onChange={onChange} />);

    // Click "4h" to add it
    const btn4h = screen.getByText("4h").closest("button");
    if (btn4h) {
      await user.click(btn4h);
    }

    expect(onChange).toHaveBeenCalled();
  });

  it("should apply presets when clicking preset buttons", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<TimeframeSelector {...defaultProps} onChange={onChange} />);

    await user.click(screen.getByText("timeframes.presetScalp"));

    expect(onChange).toHaveBeenCalledWith(["1m", "5m", "15m"]);
  });
});

// ==================== IndicatorConfig ====================

describe("IndicatorConfig", () => {
  const defaultIndicators: IndicatorSettings = {
    ema: { enabled: true, periods: [9, 21, 55] },
    rsi: { enabled: true, period: 14 },
    macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
    atr: { enabled: false, period: 14 },
  };

  const defaultProps = {
    value: defaultIndicators,
    onChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and description", () => {
    render(<IndicatorConfig {...defaultProps} />);

    expect(screen.getByText("indicators.title")).toBeInTheDocument();
    expect(screen.getByText("indicators.description")).toBeInTheDocument();
  });

  it("should render all indicator badges", () => {
    render(<IndicatorConfig {...defaultProps} />);

    expect(screen.getByText("EMA")).toBeInTheDocument();
    expect(screen.getByText("RSI")).toBeInTheDocument();
    expect(screen.getByText("MACD")).toBeInTheDocument();
    expect(screen.getByText("ATR")).toBeInTheDocument();
  });

  it("should show EMA periods when enabled", () => {
    render(<IndicatorConfig {...defaultProps} />);

    // EMA is enabled, so period inputs should be visible
    // Value "9" appears twice (EMA period + MACD signal), so use getAllBy
    const nines = screen.getAllByDisplayValue("9");
    expect(nines.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByDisplayValue("21")).toBeInTheDocument();
    expect(screen.getByDisplayValue("55")).toBeInTheDocument();
  });

  it("should show MACD parameters when enabled", () => {
    render(<IndicatorConfig {...defaultProps} />);

    expect(screen.getByDisplayValue("12")).toBeInTheDocument();
    expect(screen.getByDisplayValue("26")).toBeInTheDocument();
  });

  it("should not show ATR details when disabled", () => {
    render(<IndicatorConfig {...defaultProps} />);

    // ATR period description should not be visible (ATR is disabled)
    expect(
      screen.queryByText("indicators.atr.description")
    ).not.toBeInTheDocument();
  });
});
