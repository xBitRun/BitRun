/**
 * Tests for StrategyStudioTabs component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyStudioTabs } from "@/components/strategy-studio/strategy-studio-tabs";
import { StrategyStudioConfig, StudioTab, PromptPreviewResponse } from "@/types";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock child components
jest.mock("@/components/strategy-studio/coin-selector", () => ({
  CoinSelector: ({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) => (
    <div data-testid="coin-selector" data-value={value.join(",")}>
      <button onClick={() => onChange(["BTC", "ETH"])}>Select Coins</button>
    </div>
  ),
}));

jest.mock("@/components/strategy-studio/indicator-config", () => ({
  IndicatorConfig: ({ value, onChange }: { value: object; onChange: (v: object) => void }) => (
    <div data-testid="indicator-config">Indicator Config</div>
  ),
}));

jest.mock("@/components/strategy-studio/timeframe-selector", () => ({
  TimeframeSelector: ({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) => (
    <div data-testid="timeframe-selector">Timeframe Selector</div>
  ),
}));

jest.mock("@/components/strategy-studio/risk-controls-panel", () => ({
  RiskControlsPanel: ({ value, onChange, tradingMode, riskProfile, timeHorizon }: any) => (
    <div
      data-testid="risk-controls-panel"
      data-trading-mode={tradingMode}
      data-risk-profile={riskProfile || "none"}
      data-time-horizon={timeHorizon || "none"}
    >
      Risk Controls Panel
    </div>
  ),
}));

jest.mock("@/components/strategy-studio/prompt-template-editor", () => ({
  PromptTemplateEditor: (props: any) => (
    <div data-testid="prompt-template-editor">Prompt Template Editor</div>
  ),
}));

jest.mock("@/components/strategy-studio/prompt-preview", () => ({
  PromptPreview: ({ preview, isLoading, onRefresh, onTest, isTestLoading }: any) => (
    <div data-testid="prompt-preview" data-loading={isLoading} data-test-loading={isTestLoading}>
      <button onClick={onRefresh}>Refresh</button>
      {onTest && <button onClick={onTest}>Test AI</button>}
      Prompt Preview
    </div>
  ),
}));

jest.mock("@/components/strategy-studio/debate-config", () => ({
  DebateConfig: (props: any) => (
    <div data-testid="debate-config">Debate Config</div>
  ),
}));

// Use a module-level ref to capture onValueChange for testing
let capturedOnValueChange: ((value: string) => void) | null = null;

// Mock Tabs to provide controlled testing of onValueChange
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children, value, onValueChange, className }: {
    children: React.ReactNode;
    value: string;
    onValueChange: (value: string) => void;
    className?: string;
  }) => {
    // Capture onValueChange for test access
    capturedOnValueChange = onValueChange;
    return (
      <div data-testid="tabs" data-value={value} className={className}>
        {children}
      </div>
    );
  },
  TabsList: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div role="tablist" className={className}>{children}</div>
  ),
  TabsTrigger: ({ children, value, className }: {
    children: React.ReactNode;
    value: string;
    className?: string;
  }) => (
    <button
      role="tab"
      data-value={value}
      className={className}
      onClick={() => capturedOnValueChange?.(value)}
    >
      {children}
    </button>
  ),
  TabsContent: ({ children, value, className }: {
    children: React.ReactNode;
    value: string;
    className?: string;
  }) => (
    <div role="tabpanel" data-value={value} className={className}>{children}</div>
  ),
}));

const defaultConfig: StrategyStudioConfig = {
  symbols: ["BTC"],
  timeframes: ["1h", "4h"],
  indicators: {
    rsi: { enabled: true, period: 14, oversold: 30, overbought: 70 },
    atr: { enabled: false, period: 14, multiplier: 2 },
    macd: { enabled: false, fast: 12, slow: 26, signal: 9 },
    bollingerBands: { enabled: false, period: 20, stdDev: 2 },
    ema: { enabled: false, periods: [9, 21, 50] },
  },
  riskControls: {
    maxLeverage: 5,
    maxPositionRatio: 0.15,
    maxTotalExposure: 0.6,
    minConfidence: 65,
    minRiskRewardRatio: 2.0,
    maxDrawdownPercent: 0.2,
  },
  promptMode: "template",
  promptSections: {
    marketAnalysis: true,
    tradingStrategy: true,
    riskManagement: true,
    entryConditions: true,
    exitConditions: true,
    positionSizing: true,
  },
  customPrompt: "",
  advancedPrompt: "",
  tradingMode: "balanced",
  debateEnabled: false,
  debateModels: [],
  debateConsensusMode: "majority",
  debateMinParticipants: 2,
};

describe("StrategyStudioTabs", () => {
  const defaultProps = {
    config: defaultConfig,
    onConfigChange: jest.fn(),
    activeTab: "coins" as StudioTab,
    onTabChange: jest.fn(),
    promptPreview: null,
    isPreviewLoading: false,
    onRefreshPreview: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders all tab triggers", () => {
    render(<StrategyStudioTabs {...defaultProps} />);

    expect(screen.getByText("tabs.coins")).toBeInTheDocument();
    expect(screen.getByText("tabs.indicators")).toBeInTheDocument();
    expect(screen.getByText("tabs.risk")).toBeInTheDocument();
    expect(screen.getByText("tabs.prompt")).toBeInTheDocument();
    expect(screen.getByText("tabs.debate")).toBeInTheDocument();
    expect(screen.getByText("tabs.preview")).toBeInTheDocument();
  });

  it("renders coins tab content by default", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="coins" />);

    expect(screen.getByTestId("coin-selector")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-selector")).toBeInTheDocument();
  });

  it("renders indicators tab content", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="indicators" />);

    expect(screen.getByTestId("indicator-config")).toBeInTheDocument();
  });

  it("renders risk tab content with preset props", () => {
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="risk"
        riskProfile="conservative"
        timeHorizon="long"
      />
    );

    const riskPanel = screen.getByTestId("risk-controls-panel");
    expect(riskPanel).toBeInTheDocument();
    expect(riskPanel).toHaveAttribute("data-trading-mode", "balanced");
    expect(riskPanel).toHaveAttribute("data-risk-profile", "conservative");
    expect(riskPanel).toHaveAttribute("data-time-horizon", "long");
  });

  it("renders prompt tab content", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="prompt" />);

    expect(screen.getByTestId("prompt-template-editor")).toBeInTheDocument();
  });

  it("renders debate tab content", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="debate" />);

    expect(screen.getByTestId("debate-config")).toBeInTheDocument();
  });

  it("renders preview tab content with loading state", () => {
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        isPreviewLoading={true}
      />
    );

    const preview = screen.getByTestId("prompt-preview");
    expect(preview).toBeInTheDocument();
    expect(preview).toHaveAttribute("data-loading", "true");
  });

  it("renders preview tab with test AI button when onTestAI provided", () => {
    const onTestAI = jest.fn();
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        onTestAI={onTestAI}
        isTestLoading={false}
      />
    );

    const testButton = screen.getByText("Test AI");
    expect(testButton).toBeInTheDocument();
    
    fireEvent.click(testButton);
    expect(onTestAI).toHaveBeenCalled();
  });

  it("calls onTabChange when tab is clicked", () => {
    const onTabChange = jest.fn();
    render(
      <StrategyStudioTabs
        {...defaultProps}
        onTabChange={onTabChange}
      />
    );

    // Find the risk tab trigger by its text content and click it
    const riskTab = screen.getByText("tabs.risk");
    fireEvent.click(riskTab);
    expect(onTabChange).toHaveBeenCalledWith("risk");
  });

  it("calls onConfigChange when config is updated", () => {
    const onConfigChange = jest.fn();
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="coins"
        onConfigChange={onConfigChange}
      />
    );

    // Click the button in coin selector that triggers onChange
    fireEvent.click(screen.getByText("Select Coins"));

    expect(onConfigChange).toHaveBeenCalledWith({
      ...defaultConfig,
      symbols: ["BTC", "ETH"],
    });
  });

  it("calls onRefreshPreview when refresh button is clicked", () => {
    const onRefreshPreview = jest.fn();
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        onRefreshPreview={onRefreshPreview}
      />
    );

    fireEvent.click(screen.getByText("Refresh"));
    expect(onRefreshPreview).toHaveBeenCalled();
  });

  it("passes promptPreview to PromptPreview component", () => {
    const mockPreview: PromptPreviewResponse = {
      system_prompt: "System prompt content",
      user_prompt: "User prompt content",
      tokens_estimate: 500,
    };

    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        promptPreview={mockPreview}
      />
    );

    expect(screen.getByTestId("prompt-preview")).toBeInTheDocument();
  });
});
