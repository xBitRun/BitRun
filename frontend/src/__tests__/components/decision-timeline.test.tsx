/**
 * Tests for DecisionTimeline and DecisionStatsBar components.
 * Covers getActionColor, getActionIcon, formatTimeAgo, and all rendering paths.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import {
  DecisionTimeline,
  DecisionStatsBar,
} from "@/components/charts/decision-timeline";

// Mock lucide-react icons
jest.mock("lucide-react", () => ({
  Brain: ({ className }: { className?: string }) => (
    <svg data-testid="icon-brain" className={className} />
  ),
  TrendingUp: ({ className }: { className?: string }) => (
    <svg data-testid="icon-trending-up" className={className} />
  ),
  TrendingDown: ({ className }: { className?: string }) => (
    <svg data-testid="icon-trending-down" className={className} />
  ),
  Minus: ({ className }: { className?: string }) => (
    <svg data-testid="icon-minus" className={className} />
  ),
  Clock: ({ className }: { className?: string }) => (
    <svg data-testid="icon-clock" className={className} />
  ),
}));

// Mock cn utility
jest.mock("@/lib/utils", () => ({
  cn: (...classes: (string | undefined)[]) => classes.filter(Boolean).join(" "),
}));

const createDecision = (
  id: string,
  action: string,
  timestamp: string,
  confidence = 75,
  executed = true
) => ({
  id,
  timestamp,
  action,
  symbol: "BTC",
  confidence,
  executed,
});

describe("DecisionTimeline", () => {
  describe("Empty State", () => {
    it("renders empty state when no decisions", () => {
      render(<DecisionTimeline decisions={[]} />);

      expect(screen.getByTestId("icon-brain")).toBeInTheDocument();
      expect(screen.getByText("No decisions yet")).toBeInTheDocument();
    });

    it("applies custom className to empty state", () => {
      const { container } = render(
        <DecisionTimeline decisions={[]} className="custom-class" />
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.className).toContain("custom-class");
    });
  });

  describe("Decision Rendering", () => {
    it("renders decisions with correct icons for open_long", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString()),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-trending-up")).toBeInTheDocument();
      expect(screen.getByText("OPEN LONG")).toBeInTheDocument();
      expect(screen.getByText("BTC")).toBeInTheDocument();
    });

    it("renders decisions with correct icons for open_short", () => {
      const decisions = [
        createDecision("1", "open_short", new Date().toISOString()),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-trending-down")).toBeInTheDocument();
      expect(screen.getByText("OPEN SHORT")).toBeInTheDocument();
    });

    it("renders decisions with correct icons for close_long", () => {
      const decisions = [
        createDecision("1", "close_long", new Date().toISOString()),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-minus")).toBeInTheDocument();
      expect(screen.getByText("CLOSE LONG")).toBeInTheDocument();
    });

    it("renders decisions with correct icons for close_short", () => {
      const decisions = [
        createDecision("1", "close_short", new Date().toISOString()),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-minus")).toBeInTheDocument();
      expect(screen.getByText("CLOSE SHORT")).toBeInTheDocument();
    });

    it("renders decisions with default icon for hold action", () => {
      const decisions = [createDecision("1", "hold", new Date().toISOString())];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-clock")).toBeInTheDocument();
      expect(screen.getByText("HOLD")).toBeInTheDocument();
    });

    it("renders decisions with default icon for unknown action", () => {
      const decisions = [
        createDecision("1", "unknown_action", new Date().toISOString()),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("icon-clock")).toBeInTheDocument();
    });
  });

  describe("Confidence Display", () => {
    it("shows confidence percentage", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 85),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("displays high confidence with correct color class", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 75),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const confidenceBar = container.querySelector(
        '[style="width: 75%;"]'
      ) as HTMLElement;
      expect(confidenceBar).toBeInTheDocument();
      expect(confidenceBar.className).toContain("bg-[var(--profit)]");
    });

    it("displays medium confidence with warning color", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 55),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const confidenceBar = container.querySelector(
        '[style="width: 55%;"]'
      ) as HTMLElement;
      expect(confidenceBar).toBeInTheDocument();
      expect(confidenceBar.className).toContain("bg-[var(--warning)]");
    });

    it("displays low confidence with muted color", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 40),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const confidenceBar = container.querySelector(
        '[style="width: 40%;"]'
      ) as HTMLElement;
      expect(confidenceBar).toBeInTheDocument();
      expect(confidenceBar.className).toContain("bg-muted-foreground");
    });
  });

  describe("Execution Status", () => {
    it("shows Executed label for executed decisions", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 75, true),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("Executed")).toBeInTheDocument();
    });

    it("shows Skipped label for non-executed decisions", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString(), 75, false),
      ];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("Skipped")).toBeInTheDocument();
    });
  });

  describe("formatTimeAgo", () => {
    it('displays "just now" for very recent timestamps', () => {
      const decisions = [createDecision("1", "open_long", new Date().toISOString())];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("just now")).toBeInTheDocument();
    });

    it("displays minutes ago for timestamps within an hour", () => {
      const timestamp = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      const decisions = [createDecision("1", "open_long", timestamp)];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("5m ago")).toBeInTheDocument();
    });

    it("displays hours ago for timestamps within a day", () => {
      const timestamp = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
      const decisions = [createDecision("1", "open_long", timestamp)];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("3h ago")).toBeInTheDocument();
    });

    it("displays days ago for timestamps within a week", () => {
      const timestamp = new Date(
        Date.now() - 2 * 24 * 60 * 60 * 1000
      ).toISOString();
      const decisions = [createDecision("1", "open_long", timestamp)];
      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("2d ago")).toBeInTheDocument();
    });

    it("displays formatted date for older timestamps", () => {
      const oldDate = new Date("2024-01-15T10:00:00Z");
      const decisions = [createDecision("1", "open_long", oldDate.toISOString())];
      render(<DecisionTimeline decisions={decisions} />);

      // Should show month and day (e.g., "Jan 15")
      const timeElement = screen.getByText(/Jan.*15|15.*Jan/);
      expect(timeElement).toBeInTheDocument();
    });
  });

  describe("maxItems", () => {
    it("limits displayed decisions to maxItems", () => {
      const decisions = Array.from({ length: 15 }, (_, i) =>
        createDecision(`${i}`, "open_long", new Date().toISOString())
      );
      render(<DecisionTimeline decisions={decisions} maxItems={5} />);

      expect(screen.getAllByTestId("icon-trending-up")).toHaveLength(5);
    });

    it("shows more indicator when decisions exceed maxItems", () => {
      const decisions = Array.from({ length: 15 }, (_, i) =>
        createDecision(`${i}`, "open_long", new Date().toISOString())
      );
      render(<DecisionTimeline decisions={decisions} maxItems={10} />);

      expect(screen.getByText("+5 more decisions")).toBeInTheDocument();
    });

    it("does not show more indicator when decisions equal maxItems", () => {
      const decisions = Array.from({ length: 10 }, (_, i) =>
        createDecision(`${i}`, "open_long", new Date().toISOString())
      );
      render(<DecisionTimeline decisions={decisions} maxItems={10} />);

      expect(screen.queryByText(/more decisions/)).not.toBeInTheDocument();
    });
  });

  describe("getActionColor", () => {
    it("applies correct border/bg class for open_long", () => {
      const decisions = [
        createDecision("1", "open_long", new Date().toISOString()),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const dot = container.querySelector(".rounded-full.border-2");
      expect(dot?.className).toContain("border-[var(--profit)]");
      expect(dot?.className).toContain("bg-[var(--profit)]/10");
    });

    it("applies correct border/bg class for open_short", () => {
      const decisions = [
        createDecision("1", "open_short", new Date().toISOString()),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const dot = container.querySelector(".rounded-full.border-2");
      expect(dot?.className).toContain("border-[var(--loss)]");
      expect(dot?.className).toContain("bg-[var(--loss)]/10");
    });

    it("applies correct border/bg class for close actions", () => {
      const decisions = [
        createDecision("1", "close_long", new Date().toISOString()),
      ];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const dot = container.querySelector(".rounded-full.border-2");
      expect(dot?.className).toContain("border-muted");
      expect(dot?.className).toContain("bg-muted/30");
    });

    it("applies default border/bg class for unknown actions", () => {
      const decisions = [createDecision("1", "hold", new Date().toISOString())];
      const { container } = render(<DecisionTimeline decisions={decisions} />);

      const dot = container.querySelector(".rounded-full.border-2");
      expect(dot?.className).toContain("border-[var(--warning)]");
      expect(dot?.className).toContain("bg-[var(--warning)]/10");
    });
  });
});

describe("DecisionStatsBar", () => {
  describe("Execution Rate", () => {
    it("calculates and displays correct execution rate", () => {
      render(
        <DecisionStatsBar total={20} executed={15} actions={{ open_long: 20 }} />
      );

      expect(screen.getByText("75.0%")).toBeInTheDocument();
      expect(screen.getByText("Execution Rate")).toBeInTheDocument();
    });

    it("displays 0% execution rate when total is 0", () => {
      render(<DecisionStatsBar total={0} executed={0} actions={{}} />);

      expect(screen.getByText("0.0%")).toBeInTheDocument();
    });

    it("displays 100% execution rate when all executed", () => {
      render(
        <DecisionStatsBar total={10} executed={10} actions={{ hold: 10 }} />
      );

      expect(screen.getByText("100.0%")).toBeInTheDocument();
    });
  });

  describe("Action Distribution", () => {
    it("renders action distribution bars", () => {
      const { container } = render(
        <DecisionStatsBar
          total={100}
          executed={80}
          actions={{ open_long: 40, open_short: 30, hold: 30 }}
        />
      );

      expect(screen.getByText("Action Distribution")).toBeInTheDocument();
      // Check for distribution bars
      const bars = container.querySelectorAll('[style*="width"]');
      expect(bars.length).toBeGreaterThan(0);
    });

    it("renders action legend items", () => {
      render(
        <DecisionStatsBar
          total={100}
          executed={80}
          actions={{ open_long: 40, open_short: 30, close_long: 30 }}
        />
      );

      expect(screen.getByText(/open long: 40/i)).toBeInTheDocument();
      expect(screen.getByText(/open short: 30/i)).toBeInTheDocument();
      expect(screen.getByText(/close long: 30/i)).toBeInTheDocument();
    });

    it("skips rendering bars for 0 percentage actions", () => {
      const { container } = render(
        <DecisionStatsBar
          total={100}
          executed={80}
          actions={{ open_long: 100, open_short: 0 }}
        />
      );

      // Should only have one bar segment for open_long
      const barsContainer = container.querySelector(".flex.gap-1.h-4");
      expect(barsContainer?.children.length).toBe(1);
    });

    it("applies correct colors for different action types", () => {
      const { container } = render(
        <DecisionStatsBar
          total={100}
          executed={50}
          actions={{ open_long: 25, open_short: 25, close_long: 25, hold: 25 }}
        />
      );

      // Check legend dots have correct colors
      const dots = container.querySelectorAll(".w-2.h-2.rounded-full");
      const dotClasses = Array.from(dots).map((d) => d.className);

      expect(dotClasses.some((c) => c.includes("bg-[var(--profit)]"))).toBe(
        true
      );
      expect(dotClasses.some((c) => c.includes("bg-[var(--loss)]"))).toBe(true);
      expect(dotClasses.some((c) => c.includes("bg-muted-foreground"))).toBe(
        true
      );
      expect(dotClasses.some((c) => c.includes("bg-[var(--warning)]"))).toBe(
        true
      );
    });

    it("handles empty actions object", () => {
      render(<DecisionStatsBar total={0} executed={0} actions={{}} />);

      expect(screen.getByText("Action Distribution")).toBeInTheDocument();
      // Should not crash, just show empty distribution
    });
  });

  describe("className", () => {
    it("applies custom className", () => {
      const { container } = render(
        <DecisionStatsBar
          total={10}
          executed={5}
          actions={{}}
          className="custom-stats-class"
        />
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.className).toContain("custom-stats-class");
    });
  });
});
