/**
 * Tests for ChainOfThought component and utility functions
 */

import { render, screen, fireEvent } from "@testing-library/react";
import {
  classifyStep,
  parseSteps,
  highlightSignals,
  ChainOfThought,
} from "@/components/decisions/chain-of-thought";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    const translations: Record<string, string> = {
      chainOfThought: "Chain of Thought",
      steps: "steps",
      collapseAll: "Collapse",
      expandAll: `Expand ${params?.count ?? 0} more`,
    };
    return translations[key] || key;
  },
}));

// Mock MarkdownToggle component
jest.mock("@/components/ui/markdown-toggle", () => ({
  MarkdownToggle: ({ content }: { content: string }) => (
    <div data-testid="markdown-toggle">{content}</div>
  ),
}));

// ==================== Pure Function Tests ====================

describe("classifyStep", () => {
  it("should classify bullish patterns", () => {
    expect(classifyStep("The market is bullish")).toBe("bullish");
    expect(classifyStep("Strong uptrend detected")).toBe("bullish");
    expect(classifyStep("Price breakout above resistance")).toBe("bullish");
    expect(classifyStep("Open long position")).toBe("bullish");
    expect(classifyStep("Buy signal triggered")).toBe("bullish");
  });

  it("should classify bearish patterns", () => {
    expect(classifyStep("The market is bearish")).toBe("bearish");
    expect(classifyStep("Downtrend confirmed")).toBe("bearish");
    expect(classifyStep("Price breakdown below support")).toBe("bearish");
    expect(classifyStep("Open short position")).toBe("bearish");
    expect(classifyStep("Sell signal triggered")).toBe("bearish");
  });

  it("should classify warning patterns", () => {
    expect(classifyStep("High risk zone")).toBe("warning");
    expect(classifyStep("Caution advised")).toBe("warning");
    expect(classifyStep("Warning: volatile market")).toBe("warning");
    expect(classifyStep("Potential drawdown ahead")).toBe("warning");
  });

  it("should classify conclusion patterns", () => {
    expect(classifyStep("Conclusion: buy now")).toBe("conclusion");
    expect(classifyStep("Final decision is to hold")).toBe("conclusion");
    expect(classifyStep("Recommend opening a position")).toBe("conclusion");
    expect(classifyStep("Therefore, we should sell")).toBe("conclusion");
    expect(classifyStep("Overall trend is positive")).toBe("conclusion");
  });

  it("should prioritize conclusion over other patterns", () => {
    // Conclusion should be detected even if warning/bullish/bearish patterns exist
    expect(classifyStep("Conclusion: bullish market")).toBe("conclusion");
    expect(classifyStep("Final warning: risk")).toBe("conclusion");
  });

  it("should prioritize warning over bullish/bearish", () => {
    expect(classifyStep("Warning: bullish signal")).toBe("warning");
    expect(classifyStep("Caution: bearish market")).toBe("warning");
  });

  it("should prioritize bullish over bearish when both present", () => {
    expect(classifyStep("Bullish and bearish signals")).toBe("bullish");
  });

  it("should return neutral for no matching patterns", () => {
    expect(classifyStep("Analyzing market data")).toBe("neutral");
    expect(classifyStep("Checking indicators")).toBe("neutral");
    expect(classifyStep("")).toBe("neutral");
  });

  it("should classify Chinese patterns", () => {
    expect(classifyStep("看多信号")).toBe("bullish");
    expect(classifyStep("做多机会")).toBe("bullish");
    expect(classifyStep("突破压力位")).toBe("bullish");
    expect(classifyStep("看空市场")).toBe("bearish");
    expect(classifyStep("做空信号")).toBe("bearish");
    expect(classifyStep("风险提示")).toBe("warning");
    expect(classifyStep("结论：买入")).toBe("conclusion");
  });

  it("should be case insensitive", () => {
    expect(classifyStep("BULLISH market")).toBe("bullish");
    expect(classifyStep("BULLISH MARKET")).toBe("bullish");
    expect(classifyStep("Bullish Market")).toBe("bullish");
  });
});

describe("parseSteps", () => {
  it("should parse empty content", () => {
    expect(parseSteps("")).toEqual([]);
    expect(parseSteps("   ")).toEqual([]);
  });

  it("should split by double newlines", () => {
    const content = "Step one\n\nStep two\n\nStep three";
    const steps = parseSteps(content);

    expect(steps).toHaveLength(3);
    expect(steps[0].text).toBe("Step one");
    expect(steps[1].text).toBe("Step two");
    expect(steps[2].text).toBe("Step three");
  });

  it("should split by numbered steps", () => {
    const content = "1. First step\n2. Second step\n3. Third step";
    const steps = parseSteps(content);

    expect(steps.length).toBeGreaterThan(0);
  });

  it("should classify each step", () => {
    const content = "Bullish signal detected\n\nRisk warning\n\nConclusion: buy";
    const steps = parseSteps(content);

    expect(steps[0].type).toBe("bullish");
    expect(steps[1].type).toBe("warning");
    expect(steps[2].type).toBe("conclusion");
  });

  it("should trim whitespace from steps", () => {
    const content = "  Step one  \n\n  Step two  ";
    const steps = parseSteps(content);

    expect(steps[0].text).toBe("Step one");
    expect(steps[1].text).toBe("Step two");
  });

  it("should filter out empty steps", () => {
    const content = "Step one\n\n\n\nStep two";
    const steps = parseSteps(content);

    expect(steps.length).toBeLessThanOrEqual(2);
    steps.forEach((step) => {
      expect(step.text.length).toBeGreaterThan(0);
    });
  });

  it("should handle single step content", () => {
    const content = "Just one step";
    const steps = parseSteps(content);

    expect(steps).toHaveLength(1);
    expect(steps[0].text).toBe("Just one step");
  });
});

describe("highlightSignals", () => {
  it("should highlight RSI indicator", () => {
    const result = highlightSignals("RSI is at 70");
    expect(result).toBe("**RSI** is at 70");
  });

  it("should highlight MACD indicator", () => {
    const result = highlightSignals("MACD shows bullish crossover");
    expect(result).toBe("**MACD** shows bullish crossover");
  });

  it("should highlight EMA indicator", () => {
    const result = highlightSignals("Price above EMA 20");
    expect(result).toBe("Price above **EMA** 20");
  });

  it("should highlight ATR indicator", () => {
    const result = highlightSignals("ATR is 500");
    expect(result).toBe("**ATR** is 500");
  });

  it("should highlight SMA indicator", () => {
    const result = highlightSignals("SMA crossover detected");
    expect(result).toBe("**SMA** crossover detected");
  });

  it("should highlight BB indicator", () => {
    const result = highlightSignals("BB bands tightening");
    expect(result).toBe("**BB** bands tightening");
  });

  it("should highlight percentages", () => {
    const result = highlightSignals("Profit is 10.5%");
    expect(result).toBe("Profit is `10.5%`");
  });

  it("should highlight dollar amounts", () => {
    const result = highlightSignals("Profit of $1000");
    expect(result).toBe("Profit of `$1000`");
  });

  it("should highlight simple dollar amounts", () => {
    const result = highlightSignals("Gain of $500");
    expect(result).toBe("Gain of `$500`");
  });

  it("should highlight dollar amounts with commas", () => {
    const result = highlightSignals("Gain of $1,000.50");
    expect(result).toBe("Gain of `$1,000.50`");
  });

  it("should highlight multiple patterns", () => {
    const result = highlightSignals("RSI at 70, MACD bullish, profit 15%");
    expect(result).toBe("**RSI** at 70, **MACD** bullish, profit `15%`");
  });

  it("should be case insensitive for indicators", () => {
    const result = highlightSignals("rsi and RSI and rSi");
    // The regex preserves original case, just adds ** markers
    expect(result).toBe("**rsi** and **RSI** and **rSi**");
  });

  it("should handle content without patterns", () => {
    const result = highlightSignals("No indicators here");
    expect(result).toBe("No indicators here");
  });
});

// ==================== Component Tests ====================

describe("ChainOfThought", () => {
  it("should render markdown toggle for single step content", () => {
    render(<ChainOfThought content="Single step content" />);

    expect(screen.getByTestId("markdown-toggle")).toBeInTheDocument();
    expect(screen.getByText("Chain of Thought")).toBeInTheDocument();
  });

  it("should render timeline view for multi-step content", () => {
    const content = "Step one\n\nStep two\n\nStep three";
    render(<ChainOfThought content={content} />);

    expect(screen.getByText("Chain of Thought")).toBeInTheDocument();
    expect(screen.getByText(/3 steps/)).toBeInTheDocument();
  });

  it("should show step types", () => {
    const content = "Bullish signal\n\nBearish signal\n\nRisk warning";
    render(<ChainOfThought content={content} />);

    expect(screen.getByText("bullish")).toBeInTheDocument();
    expect(screen.getByText("bearish")).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
  });

  it("should collapse steps by default when more than initialVisibleSteps", () => {
    const content = "Step 1\n\nStep 2\n\nStep 3\n\nStep 4\n\nStep 5";
    render(<ChainOfThought content={content} initialVisibleSteps={3} />);

    // Only 3 steps should be visible - there are multiple buttons with "2 more" text
    const expandButtons = screen.getAllByText(/2 more/);
    expect(expandButtons.length).toBeGreaterThan(0);
  });

  it("should expand all steps when expand button clicked", () => {
    const content = "Step 1\n\nStep 2\n\nStep 3\n\nStep 4\n\nStep 5";
    render(<ChainOfThought content={content} initialVisibleSteps={3} />);

    const expandButtons = screen.getAllByText(/2 more/);
    fireEvent.click(expandButtons[0]);

    expect(screen.getByText("Collapse")).toBeInTheDocument();
  });

  it("should collapse steps when collapse button clicked", () => {
    const content = "Step 1\n\nStep 2\n\nStep 3\n\nStep 4\n\nStep 5";
    render(<ChainOfThought content={content} initialVisibleSteps={3} />);

    // First expand
    const expandButtons = screen.getAllByText(/2 more/);
    fireEvent.click(expandButtons[0]);

    // Then collapse
    const collapseButton = screen.getByText("Collapse");
    fireEvent.click(collapseButton);

    const expandButtonsAfter = screen.getAllByText(/2 more/);
    expect(expandButtonsAfter.length).toBeGreaterThan(0);
  });

  it("should render with custom className", () => {
    const content = "Step 1\n\nStep 2";
    render(<ChainOfThought content={content} className="custom-class" />);

    const container = screen.getByText("Chain of Thought").closest(".custom-class");
    expect(container).toBeInTheDocument();
  });

  it("should not show expand/collapse button when steps <= initialVisibleSteps", () => {
    const content = "Step 1\n\nStep 2";
    render(<ChainOfThought content={content} initialVisibleSteps={3} />);

    expect(screen.queryByText(/more/)).not.toBeInTheDocument();
  });

  it("should handle empty content", () => {
    const { container } = render(<ChainOfThought content="" />);

    // Should render something (the fallback markdown toggle with empty content)
    expect(container.firstChild).not.toBeNull();
  });

  it("should show step count in header", () => {
    const content = "Step 1\n\nStep 2\n\nStep 3";
    render(<ChainOfThought content={content} />);

    expect(screen.getByText(/3 steps/)).toBeInTheDocument();
  });

  it("should handle long steps with truncation toggle", () => {
    const longContent = "A".repeat(250);
    const content = `Step 1\n\n${longContent}\n\nStep 3`;
    render(<ChainOfThought content={content} />);

    // Long step should be clickable (cursor-pointer class)
    const stepWithLongContent = screen.getAllByText(/A{10}/)[0];
    expect(stepWithLongContent).toBeTruthy();
  });

  it("should render conclusion step with special styling", () => {
    const content = "Step 1\n\nStep 2\n\nConclusion: final decision";
    render(<ChainOfThought content={content} />);

    expect(screen.getByText("conclusion")).toBeInTheDocument();
  });
});
