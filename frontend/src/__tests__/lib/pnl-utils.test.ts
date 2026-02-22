import {
  formatPnL,
  formatPnLPercent,
  getPnLTrend,
  getPnLColor,
  formatPrice,
  formatDuration,
} from "@/lib/pnl-utils";

describe("formatPnL", () => {
  it("should format positive value with + sign by default", () => {
    expect(formatPnL(123.45)).toBe("+$123.45");
  });

  it("should format negative value with - sign by default", () => {
    expect(formatPnL(-123.45)).toBe("-$123.45");
  });

  it("should format zero without sign", () => {
    expect(formatPnL(0)).toBe("$0.00");
  });

  it("should format value without sign when showSign is false", () => {
    expect(formatPnL(123.45, false)).toBe("$123.45");
    expect(formatPnL(-123.45, false)).toBe("$123.45");
  });

  it("should respect decimal places", () => {
    expect(formatPnL(123.456, true, 3)).toBe("+$123.456");
    expect(formatPnL(123.4, true, 0)).toBe("+$123");
  });
});

describe("formatPnLPercent", () => {
  it("should format positive percent with + sign by default", () => {
    expect(formatPnLPercent(5.5)).toBe("+5.50%");
  });

  it("should format negative percent with - sign by default", () => {
    expect(formatPnLPercent(-3.25)).toBe("-3.25%");
  });

  it("should format zero without sign", () => {
    expect(formatPnLPercent(0)).toBe("0.00%");
  });

  it("should format value without sign when showSign is false", () => {
    expect(formatPnLPercent(5.5, false)).toBe("5.50%");
    expect(formatPnLPercent(-3.25, false)).toBe("3.25%");
  });

  it("should respect decimal places", () => {
    expect(formatPnLPercent(5.567, true, 1)).toBe("+5.6%");
    expect(formatPnLPercent(5.567, true, 3)).toBe("+5.567%");
  });
});

describe("getPnLTrend", () => {
  it("should return profit for positive values", () => {
    expect(getPnLTrend(0.01)).toBe("profit");
    expect(getPnLTrend(100)).toBe("profit");
  });

  it("should return loss for negative values", () => {
    expect(getPnLTrend(-0.01)).toBe("loss");
    expect(getPnLTrend(-100)).toBe("loss");
  });

  it("should return neutral for zero", () => {
    expect(getPnLTrend(0)).toBe("neutral");
  });

  it("should respect threshold", () => {
    expect(getPnLTrend(0.5, 1)).toBe("neutral");
    expect(getPnLTrend(1.5, 1)).toBe("profit");
    expect(getPnLTrend(-0.5, 1)).toBe("neutral");
    expect(getPnLTrend(-1.5, 1)).toBe("loss");
  });
});

describe("getPnLColor", () => {
  it("should return profit color for positive values", () => {
    expect(getPnLColor(100)).toBe("text-[var(--profit)]");
  });

  it("should return loss color for negative values", () => {
    expect(getPnLColor(-100)).toBe("text-[var(--loss)]");
  });

  it("should return neutral color for zero", () => {
    expect(getPnLColor(0)).toBe("text-muted-foreground");
  });
});

describe("formatPrice", () => {
  it("should format price without currency symbol", () => {
    expect(formatPrice(123.45)).toBe("123.45");
  });

  it("should respect decimal places", () => {
    expect(formatPrice(123.456, 3)).toBe("123.456");
    expect(formatPrice(123.4, 0)).toBe("123");
  });
});

describe("formatDuration", () => {
  it("should format minutes less than 60", () => {
    expect(formatDuration(30)).toBe("30m");
    expect(formatDuration(59)).toBe("59m");
  });

  it("should format hours less than 24", () => {
    expect(formatDuration(60)).toBe("1h");
    expect(formatDuration(90)).toBe("1h 30m");
    expect(formatDuration(120)).toBe("2h");
  });

  it("should format days", () => {
    expect(formatDuration(1440)).toBe("1d");
    expect(formatDuration(1500)).toBe("1d 1h");
    expect(formatDuration(2880)).toBe("2d");
  });
});
