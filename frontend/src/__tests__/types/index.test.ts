/**
 * Tests for types/index.ts – exported functions, constants, and presets
 */

import {
  presetKey,
  getStrategyPreset,
  STRATEGY_PRESETS,
  POPULAR_SYMBOLS,
  TIMEFRAME_OPTIONS,
  EXECUTION_INTERVAL_OPTIONS,
  DEFAULT_INDICATOR_SETTINGS,
  DEFAULT_RISK_CONTROLS,
  DEFAULT_STRATEGY_STUDIO_CONFIG,
  CONSENSUS_MODE_OPTIONS,
} from "@/types";
import type { RiskProfile, TimeHorizon } from "@/types";

describe("presetKey", () => {
  it("should combine risk profile and time horizon", () => {
    expect(presetKey("conservative", "scalp")).toBe("conservative_scalp");
  });

  it("should work for all risk profiles", () => {
    expect(presetKey("balanced", "swing")).toBe("balanced_swing");
    expect(presetKey("aggressive", "position")).toBe("aggressive_position");
  });
});

describe("getStrategyPreset", () => {
  it("should return the correct preset for conservative_scalp", () => {
    const preset = getStrategyPreset("conservative", "scalp");
    expect(preset).toBeDefined();
    expect(preset!.riskProfile).toBe("conservative");
    expect(preset!.timeHorizon).toBe("scalp");
    expect(preset!.values.tradingMode).toBe("conservative");
  });

  it("should return the correct preset for aggressive_swing", () => {
    const preset = getStrategyPreset("aggressive", "swing");
    expect(preset).toBeDefined();
    expect(preset!.riskProfile).toBe("aggressive");
    expect(preset!.values.tradingMode).toBe("aggressive");
  });

  it("should return undefined for invalid combination", () => {
    const preset = getStrategyPreset("invalid" as RiskProfile, "scalp" as TimeHorizon);
    expect(preset).toBeUndefined();
  });
});

describe("STRATEGY_PRESETS", () => {
  it("should contain all 9 presets (3 risk x 3 horizon)", () => {
    const riskProfiles: RiskProfile[] = ["conservative", "balanced", "aggressive"];
    const horizons: TimeHorizon[] = ["scalp", "swing", "position"];

    for (const risk of riskProfiles) {
      for (const horizon of horizons) {
        const key = presetKey(risk, horizon);
        expect(STRATEGY_PRESETS[key]).toBeDefined();
      }
    }
    expect(Object.keys(STRATEGY_PRESETS)).toHaveLength(9);
  });

  it("each preset should have required value fields", () => {
    for (const preset of Object.values(STRATEGY_PRESETS)) {
      expect(preset.values).toHaveProperty("tradingMode");
      expect(preset.values).toHaveProperty("symbols");
      expect(preset.values).toHaveProperty("timeframes");
      expect(preset.values).toHaveProperty("executionIntervalMinutes");
      expect(preset.values).toHaveProperty("indicators");
      expect(preset.values).toHaveProperty("riskControls");
    }
  });
});

describe("Constants", () => {
  it("POPULAR_SYMBOLS should contain BTC and ETH", () => {
    expect(POPULAR_SYMBOLS).toContain("BTC");
    expect(POPULAR_SYMBOLS).toContain("ETH");
    expect(POPULAR_SYMBOLS.length).toBeGreaterThanOrEqual(5);
  });

  it("TIMEFRAME_OPTIONS should have 7 entries", () => {
    expect(TIMEFRAME_OPTIONS).toHaveLength(7);
    expect(TIMEFRAME_OPTIONS[0].value).toBe("1m");
    expect(TIMEFRAME_OPTIONS[6].value).toBe("1d");
  });

  it("EXECUTION_INTERVAL_OPTIONS should have reasonable values", () => {
    expect(EXECUTION_INTERVAL_OPTIONS.length).toBeGreaterThan(0);
    const values = EXECUTION_INTERVAL_OPTIONS.map((o) => o.value);
    expect(values).toContain(15);
    expect(values).toContain(60);
  });

  it("DEFAULT_INDICATOR_SETTINGS should have all indicators enabled", () => {
    expect(DEFAULT_INDICATOR_SETTINGS.ema.enabled).toBe(true);
    expect(DEFAULT_INDICATOR_SETTINGS.rsi.enabled).toBe(true);
    expect(DEFAULT_INDICATOR_SETTINGS.macd.enabled).toBe(true);
    expect(DEFAULT_INDICATOR_SETTINGS.atr.enabled).toBe(true);
  });

  it("DEFAULT_RISK_CONTROLS should have sane defaults", () => {
    expect(DEFAULT_RISK_CONTROLS.maxLeverage).toBe(5);
    expect(DEFAULT_RISK_CONTROLS.minConfidence).toBe(60);
  });

  it("DEFAULT_STRATEGY_STUDIO_CONFIG should use conservative mode", () => {
    expect(DEFAULT_STRATEGY_STUDIO_CONFIG.tradingMode).toBe("conservative");
    expect(DEFAULT_STRATEGY_STUDIO_CONFIG.symbols).toEqual(["BTC", "ETH"]);
  });

  it("CONSENSUS_MODE_OPTIONS should have 4 modes", () => {
    expect(CONSENSUS_MODE_OPTIONS).toHaveLength(4);
    const values = CONSENSUS_MODE_OPTIONS.map((o) => o.value);
    expect(values).toContain("majority_vote");
    expect(values).toContain("unanimous");
  });
});
