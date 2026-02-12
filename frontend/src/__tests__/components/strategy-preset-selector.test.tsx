/**
 * Tests for StrategyPresetSelector component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyPresetSelector } from "@/components/strategy-studio/strategy-preset-selector";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock getStrategyPreset
jest.mock("@/types", () => ({
  ...jest.requireActual("@/types"),
  getStrategyPreset: (riskProfile: string, timeHorizon: string) => {
    if (riskProfile === "conservative" && timeHorizon === "swing") {
      return {
        values: {
          riskControls: {
            maxLeverage: 3,
            maxPositionRatio: 0.1,
            maxTotalExposure: 0.5,
            minConfidence: 75,
          },
          executionIntervalMinutes: 240,
          timeframes: ["1h", "4h"],
        },
      };
    }
    if (riskProfile === "aggressive" && timeHorizon === "scalp") {
      return {
        values: {
          riskControls: {
            maxLeverage: 20,
            maxPositionRatio: 0.3,
            maxTotalExposure: 1.0,
            minConfidence: 50,
          },
          executionIntervalMinutes: 5,
          timeframes: ["1m", "5m"],
        },
      };
    }
    return undefined;
  },
}));

describe("StrategyPresetSelector", () => {
  const defaultProps = {
    riskProfile: null as any,
    timeHorizon: null as any,
    isCustom: false,
    onSelect: jest.fn(),
    onCustom: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders all risk profile options", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(screen.getByText("riskProfile.conservative")).toBeInTheDocument();
    expect(screen.getByText("riskProfile.balanced")).toBeInTheDocument();
    expect(screen.getByText("riskProfile.aggressive")).toBeInTheDocument();
  });

  it("renders all time horizon options", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(screen.getByText("timeHorizon.scalp")).toBeInTheDocument();
    expect(screen.getByText("timeHorizon.swing")).toBeInTheDocument();
    expect(screen.getByText("timeHorizon.position")).toBeInTheDocument();
  });

  it("renders custom option", () => {
    render(<StrategyPresetSelector {...defaultProps} />);

    expect(screen.getByText("custom")).toBeInTheDocument();
    expect(screen.getByText("customDesc")).toBeInTheDocument();
  });

  it("calls onSelect when risk profile is clicked", () => {
    const onSelect = jest.fn();
    render(<StrategyPresetSelector {...defaultProps} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("riskProfile.aggressive"));

    // Should default to "swing" if no time horizon selected
    expect(onSelect).toHaveBeenCalledWith("aggressive", "swing");
  });

  it("calls onSelect with existing time horizon when risk profile is clicked", () => {
    const onSelect = jest.fn();
    render(
      <StrategyPresetSelector
        {...defaultProps}
        onSelect={onSelect}
        timeHorizon="scalp"
      />
    );

    fireEvent.click(screen.getByText("riskProfile.conservative"));

    expect(onSelect).toHaveBeenCalledWith("conservative", "scalp");
  });

  it("calls onSelect when time horizon is clicked", () => {
    const onSelect = jest.fn();
    render(<StrategyPresetSelector {...defaultProps} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("timeHorizon.scalp"));

    // Should default to "balanced" if no risk profile selected
    expect(onSelect).toHaveBeenCalledWith("balanced", "scalp");
  });

  it("calls onSelect with existing risk profile when time horizon is clicked", () => {
    const onSelect = jest.fn();
    render(
      <StrategyPresetSelector
        {...defaultProps}
        onSelect={onSelect}
        riskProfile="aggressive"
      />
    );

    fireEvent.click(screen.getByText("timeHorizon.position"));

    expect(onSelect).toHaveBeenCalledWith("aggressive", "position");
  });

  it("calls onCustom when custom option is clicked", () => {
    const onCustom = jest.fn();
    render(<StrategyPresetSelector {...defaultProps} onCustom={onCustom} />);

    fireEvent.click(screen.getByText("custom"));

    expect(onCustom).toHaveBeenCalled();
  });

  it("shows preset summary when preset is selected", () => {
    render(
      <StrategyPresetSelector
        {...defaultProps}
        riskProfile="conservative"
        timeHorizon="swing"
        isCustom={false}
      />
    );

    // Should show summary section
    expect(screen.getByText("summary.title")).toBeInTheDocument();
    expect(screen.getByText("3x")).toBeInTheDocument(); // leverage
    expect(screen.getByText("10%")).toBeInTheDocument(); // position size
    expect(screen.getByText("50%")).toBeInTheDocument(); // exposure
    expect(screen.getByText("75%")).toBeInTheDocument(); // confidence
    expect(screen.getByText("4h")).toBeInTheDocument(); // interval
  });

  it("does not show preset summary when custom is selected", () => {
    render(
      <StrategyPresetSelector
        {...defaultProps}
        riskProfile="conservative"
        timeHorizon="swing"
        isCustom={true}
      />
    );

    expect(screen.queryByText("summary.title")).not.toBeInTheDocument();
  });

  it("does not show preset summary when no preset is selected", () => {
    render(
      <StrategyPresetSelector
        {...defaultProps}
        riskProfile={null}
        timeHorizon={null}
        isCustom={false}
      />
    );

    expect(screen.queryByText("summary.title")).not.toBeInTheDocument();
  });

  it("formats interval in minutes correctly", () => {
    render(
      <StrategyPresetSelector
        {...defaultProps}
        riskProfile="aggressive"
        timeHorizon="scalp"
        isCustom={false}
      />
    );

    // 5 minutes should show as "5m"
    expect(screen.getByText("5m")).toBeInTheDocument();
  });
});
