/**
 * Tests for IndicatorConfig component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { IndicatorConfig } from "@/components/strategy-studio/indicator-config";
import { IndicatorSettings } from "@/types";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const defaultSettings: IndicatorSettings = {
  rsi: { enabled: false, period: 14 },
  atr: { enabled: false, period: 14 },
  macd: { enabled: false, fast: 12, slow: 26, signal: 9 },
  ema: { enabled: false, periods: [9, 21, 50] },
};

describe("IndicatorConfig", () => {
  it("renders all indicator sections", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig value={defaultSettings} onChange={onChange} />);

    expect(screen.getByText("indicators.title")).toBeInTheDocument();
    expect(screen.getByText("indicators.ema.title")).toBeInTheDocument();
    expect(screen.getByText("indicators.rsi.title")).toBeInTheDocument();
    expect(screen.getByText("indicators.macd.title")).toBeInTheDocument();
    expect(screen.getByText("indicators.atr.title")).toBeInTheDocument();
  });

  it("toggles RSI indicator enabled state", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig value={defaultSettings} onChange={onChange} />);

    // Find the RSI switch (second switch after EMA)
    const switches = screen.getAllByRole("switch");
    const rsiSwitch = switches[1]; // RSI is second
    
    fireEvent.click(rsiSwitch);

    expect(onChange).toHaveBeenCalledWith({
      ...defaultSettings,
      rsi: { ...defaultSettings.rsi, enabled: true },
    });
  });

  it("toggles ATR indicator enabled state", () => {
    const onChange = jest.fn();
    render(<IndicatorConfig value={defaultSettings} onChange={onChange} />);

    // ATR is the fourth switch
    const switches = screen.getAllByRole("switch");
    const atrSwitch = switches[3];
    
    fireEvent.click(atrSwitch);

    expect(onChange).toHaveBeenCalledWith({
      ...defaultSettings,
      atr: { ...defaultSettings.atr, enabled: true },
    });
  });

  it("shows RSI period slider when RSI is enabled", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      rsi: { ...defaultSettings.rsi, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    expect(screen.getByText(/indicators\.rsi\.period.*14/)).toBeInTheDocument();
    expect(screen.getByText("indicators.rsi.description")).toBeInTheDocument();
  });

  it("shows ATR period slider when ATR is enabled", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      atr: { ...defaultSettings.atr, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    expect(screen.getByText(/indicators\.atr\.period.*14/)).toBeInTheDocument();
    expect(screen.getByText("indicators.atr.description")).toBeInTheDocument();
  });

  it("shows EMA period inputs when EMA is enabled", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      ema: { ...defaultSettings.ema, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    // Should show 3 period inputs
    const inputs = screen.getAllByRole("spinbutton");
    expect(inputs.length).toBeGreaterThanOrEqual(3);
    
    // Check default values
    expect(screen.getByDisplayValue("9")).toBeInTheDocument();
    expect(screen.getByDisplayValue("21")).toBeInTheDocument();
    expect(screen.getByDisplayValue("50")).toBeInTheDocument();
  });

  it("updates EMA period and sorts them", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      ema: { ...defaultSettings.ema, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    // Change first period (9) to 100
    const input = screen.getByDisplayValue("9");
    fireEvent.change(input, { target: { value: "100" } });

    // Should be called with sorted periods
    expect(onChange).toHaveBeenCalled();
    const call = onChange.mock.calls[0][0];
    expect(call.ema.periods).toEqual([21, 50, 100]);
  });

  it("shows MACD parameters when MACD is enabled", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      macd: { ...defaultSettings.macd, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    expect(screen.getByText("indicators.macd.fast")).toBeInTheDocument();
    expect(screen.getByText("indicators.macd.slow")).toBeInTheDocument();
    expect(screen.getByText("indicators.macd.signal")).toBeInTheDocument();
    
    expect(screen.getByDisplayValue("12")).toBeInTheDocument();
    expect(screen.getByDisplayValue("26")).toBeInTheDocument();
    // Note: "9" for signal may conflict with EMA, check there's a 9
  });

  it("updates MACD fast period", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      macd: { ...defaultSettings.macd, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    const fastInput = screen.getByDisplayValue("12");
    fireEvent.change(fastInput, { target: { value: "15" } });

    expect(onChange).toHaveBeenCalledWith({
      ...enabledSettings,
      macd: { ...enabledSettings.macd, fast: 15 },
    });
  });

  it("handles invalid EMA input gracefully", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      ema: { ...defaultSettings.ema, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    const input = screen.getByDisplayValue("9");
    fireEvent.change(input, { target: { value: "" } });

    // Should default to 9
    expect(onChange).toHaveBeenCalled();
    const call = onChange.mock.calls[0][0];
    expect(call.ema.periods).toContain(9);
  });

  it("handles invalid MACD input gracefully", () => {
    const onChange = jest.fn();
    const enabledSettings: IndicatorSettings = {
      ...defaultSettings,
      macd: { ...defaultSettings.macd, enabled: true },
    };
    render(<IndicatorConfig value={enabledSettings} onChange={onChange} />);

    const fastInput = screen.getByDisplayValue("12");
    fireEvent.change(fastInput, { target: { value: "" } });

    // Should default to 12
    expect(onChange).toHaveBeenCalledWith({
      ...enabledSettings,
      macd: { ...enabledSettings.macd, fast: 12 },
    });
  });
});
