/**
 * Tests for TimeframeSelector component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { TimeframeSelector } from "@/components/strategy-studio/timeframe-selector";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock TIMEFRAME_OPTIONS
jest.mock("@/types", () => ({
  ...jest.requireActual("@/types"),
  TIMEFRAME_OPTIONS: [
    { value: "1m", label: "1 min" },
    { value: "5m", label: "5 min" },
    { value: "15m", label: "15 min" },
    { value: "1h", label: "1 hour" },
    { value: "4h", label: "4 hour" },
    { value: "1d", label: "1 day" },
    { value: "1w", label: "1 week" },
  ],
}));

describe("TimeframeSelector", () => {
  it("renders all timeframe options", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    expect(screen.getByText("1m")).toBeInTheDocument();
    expect(screen.getByText("5m")).toBeInTheDocument();
    expect(screen.getByText("15m")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("4h")).toBeInTheDocument();
    expect(screen.getByText("1d")).toBeInTheDocument();
    expect(screen.getByText("1w")).toBeInTheDocument();
  });

  it("shows selected count", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h", "4h"]} onChange={onChange} />);

    expect(screen.getByText(/2\/5/)).toBeInTheDocument();
  });

  it("adds timeframe when clicked", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("4h"));

    expect(onChange).toHaveBeenCalledWith(["1h", "4h"]);
  });

  it("removes timeframe when clicked if more than one selected", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h", "4h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("1h"));

    expect(onChange).toHaveBeenCalledWith(["4h"]);
  });

  it("does not remove last timeframe", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("1h"));

    // Should not call onChange when trying to remove the last one
    expect(onChange).not.toHaveBeenCalled();
  });

  it("disables buttons when max timeframes reached", () => {
    const onChange = jest.fn();
    render(
      <TimeframeSelector
        value={["1m", "5m", "15m", "1h", "4h"]}
        onChange={onChange}
        maxTimeframes={5}
      />
    );

    // 1d and 1w should be disabled
    const dayButton = screen.getByText("1d").closest("button");
    const weekButton = screen.getByText("1w").closest("button");

    expect(dayButton).toBeDisabled();
    expect(weekButton).toBeDisabled();
  });

  it("sorts timeframes when adding", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["4h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("1h"));

    // Should be sorted: 1h before 4h
    expect(onChange).toHaveBeenCalledWith(["1h", "4h"]);
  });

  it("applies swing preset", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("timeframes.presetSwing"));

    expect(onChange).toHaveBeenCalledWith(["15m", "1h", "4h"]);
  });

  it("applies scalp preset", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("timeframes.presetScalp"));

    expect(onChange).toHaveBeenCalledWith(["1m", "5m", "15m"]);
  });

  it("applies position preset", () => {
    const onChange = jest.fn();
    render(<TimeframeSelector value={["1h"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("timeframes.presetPosition"));

    expect(onChange).toHaveBeenCalledWith(["1h", "4h", "1d"]);
  });

  it("respects custom maxTimeframes", () => {
    const onChange = jest.fn();
    render(
      <TimeframeSelector
        value={["1h", "4h", "1d"]}
        onChange={onChange}
        maxTimeframes={3}
      />
    );

    expect(screen.getByText(/3\/3/)).toBeInTheDocument();
  });
});
