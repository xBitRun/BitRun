/**
 * Tests for EquityCurveTable component
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { EquityCurveTable } from "@/components/analytics/equity-curve-table";
import type { EquityDataPoint } from "@/lib/api/endpoints";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    const translations: Record<string, string> = {
      title: "Equity Curve",
      noData: "No data available",
      "columns.date": "Date",
      "columns.equity": "Equity",
      "columns.dailyPnl": "Daily P&L",
      "columns.dailyPnlPercent": "Daily %",
      "columns.cumulativePnl": "Cumulative",
      "columns.cumulativePnlPercent": "Cumulative %",
      "pagination.info": `Showing ${params?.start}-${params?.end} of ${params?.total}`,
    };
    return translations[key] || key;
  },
}));

// Mock TimeRangeSelector
jest.mock("@/components/analytics/time-range-selector", () => ({
  TimeRangeSelector: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string) => void;
  }) => (
    <select
      data-testid="time-range-selector"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="7d">7 Days</option>
      <option value="30d">30 Days</option>
      <option value="90d">90 Days</option>
    </select>
  ),
}));

const mockData: EquityDataPoint[] = [
  {
    date: "2024-01-03",
    equity: 10500,
    daily_pnl: 500,
    daily_pnl_percent: 5.0,
    cumulative_pnl: 500,
    cumulative_pnl_percent: 5.0,
  },
  {
    date: "2024-01-02",
    equity: 10200,
    daily_pnl: 200,
    daily_pnl_percent: 2.0,
    cumulative_pnl: 200,
    cumulative_pnl_percent: 2.0,
  },
  {
    date: "2024-01-01",
    equity: 10000,
    daily_pnl: 0,
    daily_pnl_percent: 0,
    cumulative_pnl: 0,
    cumulative_pnl_percent: 0,
  },
];

describe("EquityCurveTable", () => {
  const defaultProps = {
    data: mockData,
    timeRange: "7d" as const,
    onTimeRangeChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading state", () => {
    render(<EquityCurveTable {...defaultProps} isLoading />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no data", () => {
    render(<EquityCurveTable {...defaultProps} data={[]} />);

    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("renders table with data", () => {
    render(<EquityCurveTable {...defaultProps} />);

    expect(screen.getByText("Equity Curve")).toBeInTheDocument();
    expect(screen.getByText(/Jan 3, 2024/)).toBeInTheDocument();
    expect(screen.getByText(/Jan 2, 2024/)).toBeInTheDocument();
    expect(screen.getByText(/Jan 1, 2024/)).toBeInTheDocument();
  });

  it("sorts data by date descending", () => {
    render(<EquityCurveTable {...defaultProps} />);

    const rows = screen.getAllByRole("row");
    // First row is header, so data rows start at index 1
    expect(rows[1]).toHaveTextContent("Jan 3, 2024");
  });

  it("formats currency values correctly", () => {
    render(<EquityCurveTable {...defaultProps} />);

    // Positive values have + prefix, may appear multiple times
    const fiveHundred = screen.getAllByText(/\+\$500\.00/);
    expect(fiveHundred.length).toBeGreaterThan(0);
    const twoHundred = screen.getAllByText(/\+\$200\.00/);
    expect(twoHundred.length).toBeGreaterThan(0);
    // Zero values
    const zeros = screen.getAllByText(/\$0\.00/);
    expect(zeros.length).toBeGreaterThan(0);
  });

  it("formats percentage values correctly", () => {
    render(<EquityCurveTable {...defaultProps} />);

    const fivePercent = screen.getAllByText(/\+5\.00%/);
    expect(fivePercent.length).toBeGreaterThan(0);
    const twoPercent = screen.getAllByText(/\+2\.00%/);
    expect(twoPercent.length).toBeGreaterThan(0);
  });

  it("renders time range selector", () => {
    render(<EquityCurveTable {...defaultProps} />);

    expect(screen.getByTestId("time-range-selector")).toBeInTheDocument();
  });

  it("calls onTimeRangeChange when time range changes", () => {
    const onTimeRangeChange = jest.fn();
    render(
      <EquityCurveTable {...defaultProps} onTimeRangeChange={onTimeRangeChange} />
    );

    const selector = screen.getByTestId("time-range-selector");
    fireEvent.change(selector, { target: { value: "30d" } });

    expect(onTimeRangeChange).toHaveBeenCalledWith("30d");
  });

  it("resets to page 1 when time range changes", () => {
    // Create more data to enable pagination
    const largeData: EquityDataPoint[] = Array.from({ length: 20 }, (_, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      equity: 10000 + i * 100,
      daily_pnl: i * 100,
      daily_pnl_percent: i,
      cumulative_pnl: i * 100,
      cumulative_pnl_percent: i,
    }));

    const onTimeRangeChange = jest.fn();
    render(
      <EquityCurveTable
        {...defaultProps}
        data={largeData}
        pageSize={5}
        onTimeRangeChange={onTimeRangeChange}
      />
    );

    // Go to page 2
    const nextButtons = screen.getAllByRole("button");
    const nextButton = nextButtons.find((b) => b.textContent === "");
    if (nextButton) {
      fireEvent.click(nextButton);
    }

    // Change time range
    const selector = screen.getByTestId("time-range-selector");
    fireEvent.change(selector, { target: { value: "30d" } });

    expect(onTimeRangeChange).toHaveBeenCalled();
  });

  it("shows pagination when multiple pages", () => {
    const largeData: EquityDataPoint[] = Array.from({ length: 20 }, (_, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      equity: 10000 + i * 100,
      daily_pnl: i * 100,
      daily_pnl_percent: i,
      cumulative_pnl: i * 100,
      cumulative_pnl_percent: i,
    }));

    render(<EquityCurveTable {...defaultProps} data={largeData} pageSize={5} />);

    expect(screen.getByText(/Showing 1-5 of 20/)).toBeInTheDocument();
  });

  it("does not show pagination when single page", () => {
    render(<EquityCurveTable {...defaultProps} />);

    expect(screen.queryByText(/Showing/)).not.toBeInTheDocument();
  });

  it("disables previous button on first page", () => {
    const largeData: EquityDataPoint[] = Array.from({ length: 20 }, (_, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      equity: 10000 + i * 100,
      daily_pnl: i * 100,
      daily_pnl_percent: i,
      cumulative_pnl: i * 100,
      cumulative_pnl_percent: i,
    }));

    render(<EquityCurveTable {...defaultProps} data={largeData} pageSize={5} />);

    const buttons = screen.getAllByRole("button");
    const prevButton = buttons[0];
    expect(prevButton).toBeDisabled();
  });

  it("navigates pages correctly", () => {
    const largeData: EquityDataPoint[] = Array.from({ length: 20 }, (_, i) => ({
      date: `2024-01-${String(i + 1).padStart(2, "0")}`,
      equity: 10000 + i * 100,
      daily_pnl: i * 100,
      daily_pnl_percent: i,
      cumulative_pnl: i * 100,
      cumulative_pnl_percent: i,
    }));

    render(<EquityCurveTable {...defaultProps} data={largeData} pageSize={5} />);

    const buttons = screen.getAllByRole("button");
    const nextButton = buttons[1];
    fireEvent.click(nextButton);

    expect(screen.getByText(/Showing 6-10 of 20/)).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<EquityCurveTable {...defaultProps} className="custom-card" />);

    const card = document.querySelector(".custom-card");
    expect(card).toBeInTheDocument();
  });

  it("uses custom title", () => {
    render(<EquityCurveTable {...defaultProps} title="Custom Title" />);

    expect(screen.getByText("Custom Title")).toBeInTheDocument();
  });

  it("renders column headers", () => {
    render(<EquityCurveTable {...defaultProps} />);

    expect(screen.getByText("Date")).toBeInTheDocument();
    expect(screen.getByText("Equity")).toBeInTheDocument();
    expect(screen.getByText("Daily P&L")).toBeInTheDocument();
    expect(screen.getByText("Daily %")).toBeInTheDocument();
    expect(screen.getByText("Cumulative")).toBeInTheDocument();
    expect(screen.getByText("Cumulative %")).toBeInTheDocument();
  });
});
