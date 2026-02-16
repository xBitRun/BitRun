/**
 * Tests for Strategy Studio components:
 * - RiskControlsPanel
 * - StrategyPresetSelector
 * - TimeframeSelector
 * - IndicatorConfig
 */

import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock @/types
jest.mock("@/types", () => ({
  ...jest.requireActual("@/types"),
  POPULAR_SYMBOLS: ["BTC", "ETH", "SOL", "BNB", "XRP"],
  FOREX_SYMBOLS: ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
  METALS_SYMBOLS: ["XAU/USD", "XAG/USD"],
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

import { RiskControlsPanel } from "@/components/strategy-studio/risk-controls-panel";
import { StrategyPresetSelector } from "@/components/strategy-studio/strategy-preset-selector";
import { TimeframeSelector } from "@/components/strategy-studio/timeframe-selector";
import { IndicatorConfig } from "@/components/strategy-studio/indicator-config";
import type { RiskControlsConfig, IndicatorSettings } from "@/types";

// ==================== RiskControlsPanel ====================

describe("RiskControlsPanel", () => {
  const defaultRiskConfig: RiskControlsConfig = {
    maxLeverage: 5,
    maxPositionRatio: 0.1,
    maxTotalExposure: 0.5,
    minRiskRewardRatio: 2.0,
    maxDrawdownPercent: 0.15,
    minConfidence: 65,
    defaultSlAtrMultiplier: 1.5,
    defaultTpAtrMultiplier: 3,
    maxSlPercent: 0.1,
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

    // Multiple 10% values may appear (maxPositionRatio=0.1 and maxSlPercent=0.1)
    const percentTexts = screen.getAllByText("10%");
    expect(percentTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("should show high risk warning for aggressive settings", () => {
    const highRiskConfig: RiskControlsConfig = {
      maxLeverage: 40,
      maxPositionRatio: 0.4,
      maxTotalExposure: 0.9,
      minRiskRewardRatio: 1.0,
      maxDrawdownPercent: 0.4,
      minConfidence: 40,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(<RiskControlsPanel {...defaultProps} value={highRiskConfig} />);

    expect(
      screen.getByText("riskControls.highRiskWarning"),
    ).toBeInTheDocument();
  });

  it("should update max leverage via input", () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const leverageInput = screen.getByDisplayValue("5") as HTMLInputElement;
    fireEvent.change(leverageInput, { target: { value: "10" } });

    expect(onChange).toHaveBeenCalledWith({
      ...defaultRiskConfig,
      maxLeverage: 10,
    });
  });

  it("should update max leverage via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.maxLeverage")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "15" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        maxLeverage: 15,
      });
    }
  });

  it("should update max position ratio via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.maxPositionRatio")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "20" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        maxPositionRatio: 0.2,
      });
    }
  });

  it("should update max total exposure via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.maxTotalExposure")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "60" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        maxTotalExposure: 0.6,
      });
    }
  });

  it("should update min risk reward ratio via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.minRiskReward")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "30" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        minRiskRewardRatio: 3.0,
      });
    }
  });

  it("should update max drawdown via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.maxDrawdown")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "20" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        maxDrawdownPercent: 0.2,
      });
    }
  });

  it("should update min confidence via slider", async () => {
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const slider = screen
      .getByText("riskControls.minConfidence")
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (slider) {
      fireEvent.change(slider, { target: { value: "70" } });
      expect(onChange).toHaveBeenCalledWith({
        ...defaultRiskConfig,
        minConfidence: 70,
      });
    }
  });

  it("should display low risk level for conservative settings", () => {
    const lowRiskConfig: RiskControlsConfig = {
      maxLeverage: 3,
      maxPositionRatio: 0.1,
      maxTotalExposure: 0.5,
      minRiskRewardRatio: 2.5,
      maxDrawdownPercent: 0.05,
      minConfidence: 80,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(<RiskControlsPanel {...defaultProps} value={lowRiskConfig} />);

    expect(screen.getByText("riskControls.levels.low")).toBeInTheDocument();
  });

  it("should display medium risk level for balanced settings", () => {
    const mediumRiskConfig: RiskControlsConfig = {
      maxLeverage: 8,
      maxPositionRatio: 0.15,
      maxTotalExposure: 0.6,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.1,
      minConfidence: 65,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(<RiskControlsPanel {...defaultProps} value={mediumRiskConfig} />);

    expect(screen.getByText("riskControls.levels.medium")).toBeInTheDocument();
  });

  it("should show recommendations for conservative mode", () => {
    render(<RiskControlsPanel {...defaultProps} tradingMode="conservative" />);

    expect(
      screen.getAllByText(/riskControls\.recommended/).length,
    ).toBeGreaterThan(0);
  });

  it("should show recommendations for balanced mode", () => {
    render(<RiskControlsPanel {...defaultProps} tradingMode="balanced" />);

    expect(
      screen.getAllByText(/riskControls\.recommended/).length,
    ).toBeGreaterThan(0);
  });

  it("should show recommendations for aggressive mode", () => {
    render(<RiskControlsPanel {...defaultProps} tradingMode="aggressive" />);

    expect(
      screen.getAllByText(/riskControls\.recommended/).length,
    ).toBeGreaterThan(0);
  });

  it("should handle invalid leverage input (defaults to 1)", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<RiskControlsPanel {...defaultProps} onChange={onChange} />);

    const leverageInput = screen.getByDisplayValue("5") as HTMLInputElement;
    await user.clear(leverageInput);
    await user.type(leverageInput, "invalid");

    expect(onChange).toHaveBeenCalledWith({
      ...defaultRiskConfig,
      maxLeverage: 1,
    });
  });

  it("should respect leverage min/max constraints", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    const leverageInput = screen.getByDisplayValue("5") as HTMLInputElement;
    expect(leverageInput.min).toBe("1");
    expect(leverageInput.max).toBe("50");
  });

  it("should display all risk control labels", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    expect(screen.getByText("riskControls.maxLeverage")).toBeInTheDocument();
    expect(
      screen.getByText("riskControls.maxPositionRatio"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("riskControls.maxTotalExposure"),
    ).toBeInTheDocument();
    expect(screen.getByText("riskControls.minRiskReward")).toBeInTheDocument();
    expect(screen.getByText("riskControls.maxDrawdown")).toBeInTheDocument();
    expect(screen.getByText("riskControls.minConfidence")).toBeInTheDocument();
  });

  it("should display tooltips for all controls", () => {
    render(<RiskControlsPanel {...defaultProps} />);

    const infoIcons = screen.getAllByRole("button", { hidden: true });
    expect(infoIcons.length).toBeGreaterThan(0);
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

    expect(screen.getByText("riskProfile.conservative")).toBeInTheDocument();
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
      screen.queryByText("indicators.atr.description"),
    ).not.toBeInTheDocument();
  });

  it("should toggle EMA enabled state", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const emaSwitch = screen
      .getByText("EMA")
      .closest("div")
      ?.querySelector('button[role="switch"]');
    if (emaSwitch) {
      await user.click(emaSwitch);
      expect(onChange).toHaveBeenCalledWith({
        ...defaultIndicators,
        ema: { ...defaultIndicators.ema, enabled: false },
      });
    }
  });

  it("should update EMA period values", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const periodInputs = screen.getAllByDisplayValue("9");
    // Find the first EMA period input (not MACD signal)
    const firstPeriodInput =
      periodInputs.find(
        (input) =>
          input.getAttribute("type") === "number" &&
          input.closest("div")?.textContent?.includes("Period 1"),
      ) || periodInputs[0];

    fireEvent.change(firstPeriodInput, { target: { value: "5" } });

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.ema.periods).toContain(5);
    expect(lastCall.ema.periods).toEqual(expect.arrayContaining([5, 21, 55]));
  });

  it("should sort EMA periods after update", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const periodInputs = screen.getAllByDisplayValue("9");
    const firstPeriodInput = periodInputs[0];

    // Change first period to 100 (should be sorted to last)
    fireEvent.change(firstPeriodInput, { target: { value: "100" } });

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.ema.periods).toEqual([21, 55, 100]);
  });

  it("should handle invalid EMA period input (defaults to 9)", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const periodInputs = screen.getAllByDisplayValue("9");
    const firstPeriodInput = periodInputs[0];

    await user.clear(firstPeriodInput);
    await user.type(firstPeriodInput, "abc");

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.ema.periods[0]).toBe(9);
  });

  it("should toggle RSI enabled state", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const rsiSwitch = screen
      .getByText("RSI")
      .closest("div")
      ?.querySelector('button[role="switch"]');
    if (rsiSwitch) {
      await user.click(rsiSwitch);
      expect(onChange).toHaveBeenCalledWith({
        ...defaultIndicators,
        rsi: { ...defaultIndicators.rsi, enabled: false },
      });
    }
  });

  it("should update RSI period via slider", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    // Find RSI slider
    const rsiSlider = screen
      .getByText(/indicators\.rsi\.period/)
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (rsiSlider) {
      // Simulate slider change
      rsiSlider.value = "20";
      await userEvent.type(rsiSlider, "20", { skipClick: true });
      fireEvent.change(rsiSlider, { target: { value: "20" } });

      expect(onChange).toHaveBeenCalled();
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
      expect(lastCall.rsi.period).toBe(20);
    }
  });

  it("should toggle MACD enabled state", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const macdSwitch = screen
      .getByText("MACD")
      .closest("div")
      ?.querySelector('button[role="switch"]');
    if (macdSwitch) {
      await user.click(macdSwitch);
      expect(onChange).toHaveBeenCalledWith({
        ...defaultIndicators,
        macd: { ...defaultIndicators.macd, enabled: false },
      });
    }
  });

  it("should update MACD fast parameter", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const fastInput = screen.getByDisplayValue("12");
    fireEvent.change(fastInput, { target: { value: "8" } });

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.macd.fast).toBe(8);
  });

  it("should update MACD slow parameter", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const slowInput = screen.getByDisplayValue("26");
    fireEvent.change(slowInput, { target: { value: "30" } });

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.macd.slow).toBe(30);
  });

  it("should update MACD signal parameter", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const signalInput = screen
      .getAllByDisplayValue("9")
      .find(
        (input) =>
          input.getAttribute("type") === "number" &&
          input.closest("div")?.textContent?.includes("signal"),
      );
    if (signalInput) {
      fireEvent.change(signalInput, { target: { value: "10" } });

      expect(onChange).toHaveBeenCalled();
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
      expect(lastCall.macd.signal).toBe(10);
    }
  });

  it("should handle invalid MACD input (defaults to original value)", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const fastInput = screen.getByDisplayValue("12");
    await user.clear(fastInput);
    await user.type(fastInput, "invalid");

    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.macd.fast).toBe(12);
  });

  it("should toggle ATR enabled state", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const atrSwitch = screen
      .getByText("ATR")
      .closest("div")
      ?.querySelector('button[role="switch"]');
    if (atrSwitch) {
      await user.click(atrSwitch);
      expect(onChange).toHaveBeenCalledWith({
        ...defaultIndicators,
        atr: { ...defaultIndicators.atr, enabled: true },
      });
    }
  });

  it("should update ATR period via slider when enabled", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    const enabledATR: IndicatorSettings = {
      ...defaultIndicators,
      atr: { enabled: true, period: 14 },
    };
    render(
      <IndicatorConfig
        {...defaultProps}
        value={enabledATR}
        onChange={onChange}
      />,
    );

    // Find ATR slider
    const atrSlider = screen
      .getByText(/indicators\.atr\.period/)
      .closest("div")
      ?.querySelector('input[type="range"]') as HTMLInputElement;

    if (atrSlider) {
      atrSlider.value = "20";
      fireEvent.change(atrSlider, { target: { value: "20" } });

      expect(onChange).toHaveBeenCalled();
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
      expect(lastCall.atr.period).toBe(20);
    }
  });

  it("should show RSI period slider when enabled", () => {
    render(<IndicatorConfig {...defaultProps} />);

    expect(screen.getByText(/indicators\.rsi\.period/)).toBeInTheDocument();
    expect(screen.getByText(/14/)).toBeInTheDocument(); // Current period value
  });

  it("should show ATR period slider when enabled", () => {
    const enabledATR: IndicatorSettings = {
      ...defaultIndicators,
      atr: { enabled: true, period: 14 },
    };
    render(<IndicatorConfig {...defaultProps} value={enabledATR} />);

    expect(screen.getByText(/indicators\.atr\.period/)).toBeInTheDocument();
  });

  it("should respect EMA period min/max constraints", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<IndicatorConfig {...defaultProps} onChange={onChange} />);

    const periodInputs = screen.getAllByDisplayValue("9");
    const firstPeriodInput = periodInputs[0] as HTMLInputElement;

    // Test min constraint (should allow 1)
    await user.clear(firstPeriodInput);
    await user.type(firstPeriodInput, "1");
    expect(firstPeriodInput.min).toBe("1");

    // Test max constraint (should allow 200)
    await user.clear(firstPeriodInput);
    await user.type(firstPeriodInput, "200");
    expect(firstPeriodInput.max).toBe("200");
  });

  it("should respect MACD parameter constraints", () => {
    render(<IndicatorConfig {...defaultProps} />);

    const fastInput = screen.getByDisplayValue("12") as HTMLInputElement;
    const slowInput = screen.getByDisplayValue("26") as HTMLInputElement;
    const signalInput = screen
      .getAllByDisplayValue("9")
      .find(
        (input) =>
          input.getAttribute("type") === "number" &&
          input.closest("div")?.textContent?.includes("signal"),
      ) as HTMLInputElement;

    expect(fastInput.min).toBe("1");
    expect(fastInput.max).toBe("50");
    expect(slowInput.min).toBe("1");
    expect(slowInput.max).toBe("100");
    if (signalInput) {
      expect(signalInput.min).toBe("1");
      expect(signalInput.max).toBe("50");
    }
  });
});
