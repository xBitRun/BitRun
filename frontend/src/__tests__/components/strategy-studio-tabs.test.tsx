/**
 * Tests for StrategyStudioTabs component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyStudioTabs } from "@/components/strategy-studio/strategy-studio-tabs";
import {
  StrategyStudioConfig,
  StudioTab,
  PromptPreviewResponse,
} from "@/types";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock child components
jest.mock("@/components/symbol-selector", () => ({
  SymbolSelector: ({
    value,
    onChange,
  }: {
    value: string | string[];
    onChange: (v: string | string[]) => void;
  }) => (
    <div
      data-testid="symbol-selector"
      data-value={Array.isArray(value) ? value.join(",") : value}
    >
      <button onClick={() => onChange(["BTC", "ETH"])}>Select Symbols</button>
    </div>
  ),
}));

jest.mock("@/components/strategy-studio/indicator-config", () => ({
  IndicatorConfig: ({
    value,
    onChange,
  }: {
    value: object;
    onChange: (v: object) => void;
  }) => <div data-testid="indicator-config">Indicator Config</div>,
}));

jest.mock("@/components/strategy-studio/timeframe-selector", () => ({
  TimeframeSelector: ({
    value,
    onChange,
  }: {
    value: string[];
    onChange: (v: string[]) => void;
  }) => <div data-testid="timeframe-selector">Timeframe Selector</div>,
}));

jest.mock("@/components/strategy-studio/risk-controls-panel", () => ({
  RiskControlsPanel: ({
    value,
    onChange,
    tradingMode,
    riskProfile,
    timeHorizon,
  }: any) => (
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
  PromptPreview: ({
    preview,
    isLoading,
    onRefresh,
    onTest,
    isTestLoading,
  }: any) => (
    <div
      data-testid="prompt-preview"
      data-loading={isLoading}
      data-test-loading={isTestLoading}
    >
      <button onClick={onRefresh}>Refresh</button>
      {onTest && <button onClick={onTest}>Test AI</button>}
      Prompt Preview
    </div>
  ),
}));

// Use a module-level ref to capture onValueChange for testing
let capturedOnValueChange: ((value: string) => void) | null = null;

// Mock Tabs to provide controlled testing of onValueChange
jest.mock("@/components/ui/tabs", () => ({
  Tabs: ({
    children,
    value,
    onValueChange,
    className,
  }: {
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
  TabsList: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) => (
    <div role="tablist" className={className}>
      {children}
    </div>
  ),
  TabsTrigger: ({
    children,
    value,
    className,
  }: {
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
  TabsContent: ({
    children,
    value,
    className,
  }: {
    children: React.ReactNode;
    value: string;
    className?: string;
  }) => (
    <div role="tabpanel" data-value={value} className={className}>
      {children}
    </div>
  ),
}));

const defaultConfig: StrategyStudioConfig = {
  name: "Test Strategy",
  description: "Test description",
  accountId: "account-1",
  aiModel: "gpt-4",
  symbols: ["BTC"],
  timeframes: ["1h", "4h"],
  executionIntervalMinutes: 30,
  autoExecute: true,
  indicators: {
    rsi: { enabled: true, period: 14 },
    atr: { enabled: false, period: 14 },
    macd: { enabled: false, fast: 12, slow: 26, signal: 9 },
    ema: { enabled: false, periods: [9, 21, 50] },
  },
  riskControls: {
    maxLeverage: 5,
    maxPositionRatio: 0.15,
    maxTotalExposure: 0.6,
    minConfidence: 65,
    minRiskRewardRatio: 2.0,
    maxDrawdownPercent: 0.2,
    defaultSlAtrMultiplier: 1.5,
    defaultTpAtrMultiplier: 3.0,
    maxSlPercent: 5,
  },
  language: "en",
  promptMode: "simple",
  promptSections: {
    roleDefinition: "",
    tradingFrequency: "",
    entryStandards: "",
    decisionProcess: "",
  },
  customPrompt: "",
  advancedPrompt: "",
  tradingMode: "balanced",
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
    expect(screen.getByText("tabs.preview")).toBeInTheDocument();
  });

  it("renders coins tab content by default", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="coins" />);

    expect(screen.getByTestId("symbol-selector")).toBeInTheDocument();
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
        timeHorizon="position"
      />,
    );

    const riskPanel = screen.getByTestId("risk-controls-panel");
    expect(riskPanel).toBeInTheDocument();
    expect(riskPanel).toHaveAttribute("data-trading-mode", "balanced");
    expect(riskPanel).toHaveAttribute("data-risk-profile", "conservative");
    expect(riskPanel).toHaveAttribute("data-time-horizon", "position");
  });

  it("renders prompt tab content", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="prompt" />);

    expect(screen.getByTestId("prompt-template-editor")).toBeInTheDocument();
  });

  it("renders preview tab content with loading state", () => {
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        isPreviewLoading={true}
      />,
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
      />,
    );

    const testButton = screen.getByText("Test AI");
    expect(testButton).toBeInTheDocument();

    fireEvent.click(testButton);
    expect(onTestAI).toHaveBeenCalled();
  });

  it("calls onTabChange when tab is clicked", () => {
    const onTabChange = jest.fn();
    render(<StrategyStudioTabs {...defaultProps} onTabChange={onTabChange} />);

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
      />,
    );

    // Click the button in symbol selector that triggers onChange
    fireEvent.click(screen.getByText("Select Symbols"));

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
      />,
    );

    fireEvent.click(screen.getByText("Refresh"));
    expect(onRefreshPreview).toHaveBeenCalled();
  });

  it("passes promptPreview to PromptPreview component", () => {
    const mockPreview: PromptPreviewResponse = {
      systemPrompt: "System prompt content",
      estimatedTokens: 500,
      sections: {
        roleDefinition: "",
        tradingMode: "",
        tradingFrequency: "",
        entryStandards: "",
        decisionProcess: "",
        customPrompt: "",
      },
    };

    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="preview"
        promptPreview={mockPreview}
      />,
    );

    expect(screen.getByTestId("prompt-preview")).toBeInTheDocument();
  });
});
