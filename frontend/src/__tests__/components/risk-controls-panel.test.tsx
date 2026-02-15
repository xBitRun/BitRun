/**
 * Tests for RiskControlsPanel component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { RiskControlsPanel } from "@/components/strategy-studio/risk-controls-panel";
import { RiskControlsConfig, TradingMode, RiskProfile, TimeHorizon } from "@/types";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: (namespace: string) => (key: string, params?: Record<string, unknown>) => {
    // Return interpolated strings for testing
    if (params) {
      return `${key}:${JSON.stringify(params)}`;
    }
    return key;
  },
}));

// Mock Tooltip components
jest.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip-content">{children}</div>
  ),
}));

// Mock getStrategyPreset
jest.mock("@/types", () => ({
  ...jest.requireActual("@/types"),
  getStrategyPreset: (riskProfile: string, timeHorizon: string) => {
    // Return mock preset values for testing
    if (riskProfile === "conservative" && timeHorizon === "long") {
      return {
        values: {
          riskControls: {
            maxLeverage: 3,
            maxPositionRatio: 0.1,
            maxTotalExposure: 0.5,
            minConfidence: 75,
          },
        },
      };
    }
    if (riskProfile === "aggressive" && timeHorizon === "short") {
      return {
        values: {
          riskControls: {
            maxLeverage: 20,
            maxPositionRatio: 0.3,
            maxTotalExposure: 1.0,
            minConfidence: 50,
          },
        },
      };
    }
    return null;
  },
}));

// Default config with values calculated to produce "medium" risk level (score 31-60)
// Score calculation:
// - maxLeverage: (15/50) * 40 = 12
// - maxPositionRatio: (0.25/0.5) * 25 = 12.5
// - maxTotalExposure: (0.7/1.0) * 20 = 14
// - minConfidence: ((100-60)/100) * 15 = 6
// Total = 44.5 → "medium"
const defaultConfig: RiskControlsConfig = {
  maxLeverage: 15,
  maxPositionRatio: 0.25,
  maxTotalExposure: 0.7,
  minConfidence: 60,
  minRiskRewardRatio: 2.0,
  maxDrawdownPercent: 0.2,
  defaultSlAtrMultiplier: 1.5,
  defaultTpAtrMultiplier: 3,
  maxSlPercent: 0.1,
};

describe("RiskControlsPanel", () => {
  it("renders all risk control inputs", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    // Check labels are rendered
    expect(screen.getByText("riskControls.maxLeverage")).toBeInTheDocument();
    expect(screen.getByText("riskControls.maxPositionRatio")).toBeInTheDocument();
    expect(screen.getByText("riskControls.maxTotalExposure")).toBeInTheDocument();
    expect(screen.getByText("riskControls.minConfidence")).toBeInTheDocument();
    expect(screen.getByText("riskControls.minRiskReward")).toBeInTheDocument();
    expect(screen.getByText("riskControls.maxDrawdown")).toBeInTheDocument();
  });

  it("displays current values", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    // Check that current values are displayed (defaultConfig values)
    expect(screen.getByDisplayValue("15")).toBeInTheDocument(); // maxLeverage
    expect(screen.getByText("25%")).toBeInTheDocument(); // maxPositionRatio
    expect(screen.getByText("70%")).toBeInTheDocument(); // maxTotalExposure
    expect(screen.getByText("60%")).toBeInTheDocument(); // minConfidence
  });

  it("calls onChange when leverage input changes", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    // defaultConfig.maxLeverage is 15
    const input = screen.getByDisplayValue("15");
    fireEvent.change(input, { target: { value: "10" } });

    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      maxLeverage: 10,
    });
  });

  it("displays low risk level for conservative settings", () => {
    const onChange = jest.fn();
    const lowRiskConfig: RiskControlsConfig = {
      maxLeverage: 2,
      maxPositionRatio: 0.05,
      maxTotalExposure: 0.3,
      minConfidence: 90,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.1,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={lowRiskConfig}
        onChange={onChange}
        tradingMode="conservative"
      />
    );

    expect(screen.getByText("riskControls.levels.low")).toBeInTheDocument();
  });

  it("displays high risk level for aggressive settings", () => {
    const onChange = jest.fn();
    const highRiskConfig: RiskControlsConfig = {
      maxLeverage: 50,
      maxPositionRatio: 0.5,
      maxTotalExposure: 1.0,
      minConfidence: 30,
      minRiskRewardRatio: 1.0,
      maxDrawdownPercent: 0.5,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={highRiskConfig}
        onChange={onChange}
        tradingMode="aggressive"
      />
    );

    expect(screen.getByText("riskControls.levels.high")).toBeInTheDocument();
    // High risk warning should be shown
    expect(screen.getByText("riskControls.highRiskWarning")).toBeInTheDocument();
  });

  it("displays medium risk level for balanced settings", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    expect(screen.getByText("riskControls.levels.medium")).toBeInTheDocument();
  });

  it("shows conservative mode mismatch warning", () => {
    const onChange = jest.fn();
    const aggressiveInConservative: RiskControlsConfig = {
      maxLeverage: 15, // Too high for conservative
      maxPositionRatio: 0.25, // Too high
      maxTotalExposure: 0.8, // Too high
      minConfidence: 50, // Too low
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={aggressiveInConservative}
        onChange={onChange}
        tradingMode="conservative"
      />
    );

    expect(screen.getByText("riskControls.modeMismatchConservative")).toBeInTheDocument();
  });

  it("shows aggressive mode mismatch warning", () => {
    const onChange = jest.fn();
    const conservativeInAggressive: RiskControlsConfig = {
      maxLeverage: 2, // Too low for aggressive
      maxPositionRatio: 0.1, // Too low
      maxTotalExposure: 0.4, // Too low
      minConfidence: 80, // Too high
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={conservativeInAggressive}
        onChange={onChange}
        tradingMode="aggressive"
      />
    );

    expect(screen.getByText("riskControls.modeMismatchAggressive")).toBeInTheDocument();
  });

  it("shows balanced mode mismatch warning for too high leverage", () => {
    const onChange = jest.fn();
    const tooHighForBalanced: RiskControlsConfig = {
      maxLeverage: 15, // Too high for balanced
      maxPositionRatio: 0.15,
      maxTotalExposure: 0.6,
      minConfidence: 65,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={tooHighForBalanced}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    expect(screen.getByText("riskControls.modeMismatchBalanced")).toBeInTheDocument();
  });

  it("shows balanced mode mismatch warning for too low leverage", () => {
    const onChange = jest.fn();
    const tooLowForBalanced: RiskControlsConfig = {
      maxLeverage: 2, // Too low for balanced
      maxPositionRatio: 0.15,
      maxTotalExposure: 0.6,
      minConfidence: 65,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={tooLowForBalanced}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    expect(screen.getByText("riskControls.modeMismatchBalanced")).toBeInTheDocument();
  });

  it("shows preset-based mismatch when values deviate from preset", () => {
    const onChange = jest.fn();
    // Using conservative/long preset which expects maxLeverage=3
    // But we're using maxLeverage=10 (> 50% deviation)
    const deviatedConfig: RiskControlsConfig = {
      maxLeverage: 10, // Expected: 3, deviation > 50%
      maxPositionRatio: 0.1,
      maxTotalExposure: 0.5,
      minConfidence: 75,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={deviatedConfig}
        onChange={onChange}
        tradingMode="conservative"
        riskProfile="conservative"
        timeHorizon="long"
      />
    );

    // Should show preset mismatch with deviation details
    const warnings = screen.getAllByText(/riskControls\.presetMismatch/);
    expect(warnings.length).toBeGreaterThan(0);
  });

  it("does not show mismatch warning when values match preset", () => {
    const onChange = jest.fn();
    // Matching the conservative/long preset exactly
    const matchingConfig: RiskControlsConfig = {
      maxLeverage: 3,
      maxPositionRatio: 0.1,
      maxTotalExposure: 0.5,
      minConfidence: 75,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.2,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3,
      maxSlPercent: 0.1,
    };
    render(
      <RiskControlsPanel
        value={matchingConfig}
        onChange={onChange}
        tradingMode="conservative"
        riskProfile="conservative"
        timeHorizon="long"
      />
    );

    // Should not show any mismatch warnings
    expect(screen.queryByText(/modeMismatch/)).not.toBeInTheDocument();
    expect(screen.queryByText(/presetMismatch/)).not.toBeInTheDocument();
  });

  it("shows preset-based recommendations", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="conservative"
        riskProfile="conservative"
        timeHorizon="long"
      />
    );

    // Should show "3x" as recommendation for maxLeverage
    expect(screen.getByText(/riskControls\.recommended.*3x/)).toBeInTheDocument();
  });

  it("falls back to tradingMode recommendations when no preset", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="aggressive"
      />
    );

    // Should show aggressive mode range recommendations
    expect(screen.getByText(/riskControls\.recommended.*10-20x/)).toBeInTheDocument();
  });

  it("handles invalid leverage input gracefully", () => {
    const onChange = jest.fn();
    render(
      <RiskControlsPanel
        value={defaultConfig}
        onChange={onChange}
        tradingMode="balanced"
      />
    );

    // defaultConfig.maxLeverage is 15
    const input = screen.getByDisplayValue("15");
    fireEvent.change(input, { target: { value: "" } });

    // Should default to 1 when input is invalid
    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      maxLeverage: 1,
    });
  });
});
