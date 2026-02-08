/**
 * Tests for Chart components:
 * - PerformanceChart
 * - Sparkline
 * - DecisionTimeline
 * - DecisionStatsBar
 */

import { render, screen } from "@testing-library/react";
import React from "react";

import {
  PerformanceChart,
  Sparkline,
} from "@/components/charts/performance-chart";
import {
  DecisionTimeline,
  DecisionStatsBar,
} from "@/components/charts/decision-timeline";

// ==================== PerformanceChart ====================

describe("PerformanceChart", () => {
  it("should show empty state when no data provided", () => {
    render(<PerformanceChart data={[]} />);

    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("should render SVG when data is provided", () => {
    const data = [
      { timestamp: "2024-01-01", value: 5 },
      { timestamp: "2024-01-02", value: 10 },
      { timestamp: "2024-01-03", value: 8 },
    ];

    const { container } = render(<PerformanceChart data={data} />);

    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("should display min/max labels when showLabels is true", () => {
    const data = [
      { timestamp: "2024-01-01", value: 2 },
      { timestamp: "2024-01-02", value: 10 },
    ];

    render(<PerformanceChart data={data} showLabels={true} />);

    // Should display formatted max value
    expect(screen.getByText("+10.0%")).toBeInTheDocument();
    expect(screen.getByText("+2.0%")).toBeInTheDocument();
  });

  it("should not display labels when showLabels is false", () => {
    const data = [
      { timestamp: "2024-01-01", value: 2 },
      { timestamp: "2024-01-02", value: 10 },
    ];

    render(<PerformanceChart data={data} showLabels={false} />);

    expect(screen.queryByText("+10.0%")).not.toBeInTheDocument();
  });
});

// ==================== Sparkline ====================

describe("Sparkline", () => {
  it("should render placeholder when data is insufficient", () => {
    const { container } = render(<Sparkline data={[]} />);

    // Should render a div placeholder, not an SVG
    expect(container.querySelector("svg")).not.toBeInTheDocument();
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("should render SVG when valid data is provided", () => {
    const { container } = render(<Sparkline data={[1, 2, 3, 4, 5]} />);

    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(container.querySelector("path")).toBeInTheDocument();
  });
});

// ==================== DecisionTimeline ====================

describe("DecisionTimeline", () => {
  const mockDecisions = [
    {
      id: "1",
      timestamp: new Date().toISOString(),
      action: "open_long",
      symbol: "BTC",
      confidence: 80,
      executed: true,
    },
    {
      id: "2",
      timestamp: new Date().toISOString(),
      action: "open_short",
      symbol: "ETH",
      confidence: 65,
      executed: false,
    },
  ];

  it("should show empty state when no decisions", () => {
    render(<DecisionTimeline decisions={[]} />);

    expect(screen.getByText("No decisions yet")).toBeInTheDocument();
  });

  it("should render decisions with action and symbol", () => {
    render(<DecisionTimeline decisions={mockDecisions} />);

    expect(screen.getByText("OPEN LONG")).toBeInTheDocument();
    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("OPEN SHORT")).toBeInTheDocument();
    expect(screen.getByText("ETH")).toBeInTheDocument();
  });

  it("should display confidence percentages", () => {
    render(<DecisionTimeline decisions={mockDecisions} />);

    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();
  });

  it("should show executed/skipped status", () => {
    render(<DecisionTimeline decisions={mockDecisions} />);

    expect(screen.getByText("Executed")).toBeInTheDocument();
    expect(screen.getByText("Skipped")).toBeInTheDocument();
  });

  it("should show 'more' indicator when decisions exceed maxItems", () => {
    const manyDecisions = Array.from({ length: 15 }, (_, i) => ({
      id: `${i}`,
      timestamp: new Date().toISOString(),
      action: "open_long",
      symbol: "BTC",
      confidence: 75,
      executed: true,
    }));

    render(<DecisionTimeline decisions={manyDecisions} maxItems={10} />);

    expect(screen.getByText("+5 more decisions")).toBeInTheDocument();
  });
});

// ==================== DecisionStatsBar ====================

describe("DecisionStatsBar", () => {
  it("should display execution rate", () => {
    render(
      <DecisionStatsBar
        total={10}
        executed={8}
        actions={{ open_long: 5, open_short: 3, hold: 2 }}
      />
    );

    expect(screen.getByText("Execution Rate")).toBeInTheDocument();
    expect(screen.getByText("80.0%")).toBeInTheDocument();
  });

  it("should display action distribution", () => {
    render(
      <DecisionStatsBar
        total={10}
        executed={8}
        actions={{ open_long: 5, open_short: 3, hold: 2 }}
      />
    );

    expect(screen.getByText("Action Distribution")).toBeInTheDocument();
    expect(screen.getByText(/open long: 5/)).toBeInTheDocument();
    expect(screen.getByText(/open short: 3/)).toBeInTheDocument();
  });
});
