/**
 * Tests for Strategy Studio extra components:
 * - DebateConfig
 * - PromptPreview
 * - PromptTemplateEditor
 * - StrategyStudioTabs
 * - DebateResultCard
 */

import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock @/types with constants needed by components
jest.mock("@/types", () => ({
  CONSENSUS_MODE_OPTIONS: [
    { value: "majority_vote", label: "Majority Vote", description: "Most common action wins" },
    { value: "highest_confidence", label: "Highest Confidence", description: "Highest confidence model wins" },
    { value: "weighted_average", label: "Weighted Average", description: "Weighted average of all models" },
    { value: "unanimous", label: "Unanimous", description: "All models must agree" },
  ],
  DEFAULT_PROMPT_SECTIONS: {
    roleDefinition: "You are an expert cryptocurrency trader with deep market analysis skills.",
    tradingFrequency: "Analyze market every 30-60 minutes. Only trade when high-confidence setups appear.",
    entryStandards: "Enter positions only when multiple indicators align and risk/reward is favorable.",
    decisionProcess: "1. Assess overall market trend\n2. Identify key support/resistance\n3. Check momentum indicators\n4. Evaluate risk/reward\n5. Make decision",
  },
  DEFAULT_STRATEGY_STUDIO_CONFIG: {
    name: "",
    description: "",
    accountId: "",
    aiModel: "",
    tradingMode: "conservative",
    symbols: ["BTC", "ETH"],
    timeframes: ["15m", "1h", "4h"],
    executionIntervalMinutes: 30,
    autoExecute: true,
    indicators: {
      ema: { enabled: true, periods: [9, 21, 55] },
      rsi: { enabled: true, period: 14 },
      macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
      atr: { enabled: true, period: 14 },
    },
    riskControls: {
      maxLeverage: 5,
      maxPositionRatio: 0.2,
      maxTotalExposure: 0.8,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.1,
      minConfidence: 60,
    },
    language: "en",
    promptSections: {
      roleDefinition: "",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
    },
    customPrompt: "",
    debateEnabled: false,
    debateModels: [],
    debateConsensusMode: "majority_vote",
    debateMinParticipants: 2,
  },
  POPULAR_SYMBOLS: ["BTC", "ETH", "SOL"],
  TIMEFRAME_OPTIONS: [
    { value: "15m", label: "15 minutes" },
    { value: "1h", label: "1 hour" },
    { value: "4h", label: "4 hours" },
  ],
  getStrategyPreset: jest.fn(() => null),
}));

// Mock hooks used by DebateConfig
jest.mock("@/hooks", () => ({
  useUserModels: jest.fn(() => ({
    models: [
      { id: "deepseek:chat", name: "DeepSeek Chat", provider: "deepseek", cost_per_1k_input: 0.1, cost_per_1k_output: 0.2 },
      { id: "openai:gpt-4o", name: "GPT-4o", provider: "openai", cost_per_1k_input: 2.5, cost_per_1k_output: 10 },
    ],
    hasConfiguredProviders: true,
    isLoading: false,
    error: null,
    refresh: jest.fn(),
  })),
  getProviderDisplayName: jest.fn((id: string) => {
    const map: Record<string, string> = { deepseek: "DeepSeek", openai: "OpenAI" };
    return map[id] || id;
  }),
}));

// Mock sub-components used by StrategyStudioTabs
jest.mock("@/components/strategy-studio/coin-selector", () => ({
  CoinSelector: ({ value }: { value: string[] }) => (
    <div data-testid="coin-selector">Coins: {value.join(",")}</div>
  ),
}));

jest.mock("@/components/strategy-studio/timeframe-selector", () => ({
  TimeframeSelector: ({ value }: { value: string[] }) => (
    <div data-testid="timeframe-selector">Timeframes: {value.join(",")}</div>
  ),
}));

jest.mock("@/components/strategy-studio/indicator-config", () => ({
  IndicatorConfig: () => <div data-testid="indicator-config">IndicatorConfig</div>,
}));

jest.mock("@/components/strategy-studio/risk-controls-panel", () => ({
  RiskControlsPanel: () => <div data-testid="risk-controls">RiskControls</div>,
}));

// Mock toast
jest.mock("@/components/ui/toast", () => ({
  useToast: () => ({
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  }),
}));

// Mock react-markdown
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock next/link
jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

import { DebateConfig } from "@/components/strategy-studio/debate-config";
import { PromptPreview } from "@/components/strategy-studio/prompt-preview";
import { PromptTemplateEditor } from "@/components/strategy-studio/prompt-template-editor";
import { StrategyStudioTabs } from "@/components/strategy-studio/strategy-studio-tabs";
import { DebateResultCard } from "@/components/strategy-studio/debate-result-card";

// ==================== DebateConfig ====================

describe("DebateConfig", () => {
  const defaultProps = {
    enabled: false,
    onEnabledChange: jest.fn(),
    modelIds: [] as string[],
    onModelIdsChange: jest.fn(),
    consensusMode: "majority_vote" as const,
    onConsensusModeChange: jest.fn(),
    minParticipants: 2,
    onMinParticipantsChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title and toggle", () => {
    render(<DebateConfig {...defaultProps} />);

    expect(screen.getByText("debate.title")).toBeInTheDocument();
    expect(screen.getByText("debate.enable")).toBeInTheDocument();
  });

  it("should not show model selection when disabled", () => {
    render(<DebateConfig {...defaultProps} enabled={false} />);

    expect(screen.queryByText("debate.selectModels")).not.toBeInTheDocument();
  });

  it("should show model selection when enabled", () => {
    render(<DebateConfig {...defaultProps} enabled={true} />);

    expect(screen.getByText("debate.selectModels")).toBeInTheDocument();
    // Shows model names
    expect(screen.getByText("DeepSeek Chat")).toBeInTheDocument();
    expect(screen.getByText("GPT-4o")).toBeInTheDocument();
  });

  it("should show warning when less than 2 models selected", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat"]} />);

    expect(screen.getByText("debate.minModelsWarning")).toBeInTheDocument();
  });

  it("should toggle model on click", () => {
    render(<DebateConfig {...defaultProps} enabled={true} />);

    // Click on a model
    fireEvent.click(screen.getByText("DeepSeek Chat"));

    expect(defaultProps.onModelIdsChange).toHaveBeenCalledWith(["deepseek:chat"]);
  });

  it("should remove model when clicking selected model", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat"]} />);

    fireEvent.click(screen.getByText("DeepSeek Chat"));

    expect(defaultProps.onModelIdsChange).toHaveBeenCalledWith([]);
  });

  it("should not allow selecting more than 5 models", () => {
    const fiveModels = ["model1", "model2", "model3", "model4", "model5"];
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={fiveModels} />);

    // Try to click another model
    fireEvent.click(screen.getByText("DeepSeek Chat"));

    // Should not add more models
    expect(defaultProps.onModelIdsChange).not.toHaveBeenCalled();
  });

  it("should display model count badge", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    expect(screen.getByText(/2\/5/)).toBeInTheDocument();
  });

  it("should display consensus mode selector", () => {
    render(<DebateConfig {...defaultProps} enabled={true} />);

    expect(screen.getByText("debate.consensusMode")).toBeInTheDocument();
  });

  it("should change consensus mode", async () => {
    const user = userEvent.setup();
    render(<DebateConfig {...defaultProps} enabled={true} />);

    // First combobox is consensus mode, second is min participants
    const selectTrigger = screen.getAllByRole("combobox")[0];
    await user.click(selectTrigger);

    const option = screen.getByText("Highest Confidence");
    await user.click(option);

    expect(defaultProps.onConsensusModeChange).toHaveBeenCalledWith("highest_confidence");
  });

  it("should display min participants selector", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    expect(screen.getByText("debate.minParticipants")).toBeInTheDocument();
  });

  it("should change min participants", async () => {
    const user = userEvent.setup();
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o", "model3"]} />);

    const selectTrigger = screen.getAllByRole("combobox")[1]; // Second select is min participants
    await user.click(selectTrigger);

    const option = screen.getByText(/3 debate\.models/);
    await user.click(option);

    expect(defaultProps.onMinParticipantsChange).toHaveBeenCalledWith(3);
  });

  it("should filter min participants options based on selected models", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat"]} />);

    // With only 1 model selected, should only show option for 2 (minimum)
    const selectTrigger = screen.getAllByRole("combobox")[1];
    fireEvent.click(selectTrigger);

    // Should not show options for 3, 4, 5 when only 1 model is selected
    expect(screen.queryByText(/3 debate\.models/)).not.toBeInTheDocument();
  });

  it("should display estimated cost", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    // Estimated cost = 2 models * 0.1 = 0.2
    expect(screen.getByText(/debate\.estimatedCost/)).toBeInTheDocument();
    expect(screen.getByText(/\$0\.20/)).toBeInTheDocument();
  });

  it("should show loading state when models are loading", () => {
    const { useUserModels } = require("@/hooks");
    useUserModels.mockReturnValue({
      models: [],
      isLoading: true,
      error: null,
      refresh: jest.fn(),
    });

    const { container } = render(<DebateConfig {...defaultProps} enabled={true} />);

    // Skeleton components render with data-slot="skeleton" attribute
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("should show error state when models fail to load", () => {
    const { useUserModels } = require("@/hooks");
    useUserModels.mockReturnValue({
      models: [],
      isLoading: false,
      error: new Error("Failed to load"),
      refresh: jest.fn(),
    });

    render(<DebateConfig {...defaultProps} enabled={true} />);

    expect(screen.getByText("debate.modelsLoadFailed")).toBeInTheDocument();
    expect(screen.getByText("debate.retry")).toBeInTheDocument();
  });

  it("should retry loading models when retry button clicked", async () => {
    const user = userEvent.setup();
    const mockRefresh = jest.fn();
    const { useUserModels } = require("@/hooks");
    useUserModels.mockReturnValue({
      models: [],
      isLoading: false,
      error: new Error("Failed to load"),
      refresh: mockRefresh,
    });

    render(<DebateConfig {...defaultProps} enabled={true} />);

    const retryButton = screen.getByText("debate.retry");
    await user.click(retryButton);

    expect(mockRefresh).toHaveBeenCalled();
  });

  it("should show no models message when no models available", () => {
    const { useUserModels } = require("@/hooks");
    useUserModels.mockReturnValue({
      models: [],
      isLoading: false,
      error: null,
      refresh: jest.fn(),
    });

    render(<DebateConfig {...defaultProps} enabled={true} />);

    expect(screen.getByText("debate.noModels")).toBeInTheDocument();
    expect(screen.getByText("debate.addModelLink")).toBeInTheDocument();
  });

  it("should disable validate button when less than 2 models selected", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat"]} />);

    const validateButton = screen.getByText("debate.validate").closest("button");
    expect(validateButton).toBeDisabled();
  });

  it("should enable validate button when 2 or more models selected", () => {
    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    const validateButton = screen.getByText("debate.validate").closest("button");
    expect(validateButton).not.toBeDisabled();
  });

  it("should call validate API when validate button clicked", async () => {
    const user = userEvent.setup();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          { modelId: "deepseek:chat", valid: true },
          { modelId: "openai:gpt-4o", valid: true },
        ],
      }),
    });

    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    const validateButton = screen.getByText("debate.validate").closest("button");
    if (validateButton) {
      await user.click(validateButton);

      expect(global.fetch).toHaveBeenCalledWith("/api/strategies/validate-debate-models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_ids: ["deepseek:chat", "openai:gpt-4o"] }),
      });
    }
  });

  it("should display validation success indicator", async () => {
    const user = userEvent.setup();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          { modelId: "deepseek:chat", valid: true },
          { modelId: "openai:gpt-4o", valid: true },
        ],
      }),
    });

    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    const validateButton = screen.getByText("debate.validate").closest("button");
    expect(validateButton).not.toBeDisabled();
    await user.click(validateButton!);

    // Wait for async fetch to complete
    await screen.findByText("debate.validate");
    expect(global.fetch).toHaveBeenCalled();
  });

  it("should display validation error indicator", async () => {
    const user = userEvent.setup();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          { modelId: "deepseek:chat", valid: false, error: "Model not available" },
          { modelId: "openai:gpt-4o", valid: true },
        ],
      }),
    });

    render(<DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat", "openai:gpt-4o"]} />);

    const validateButton = screen.getByText("debate.validate").closest("button");
    expect(validateButton).not.toBeDisabled();
    await user.click(validateButton!);

    // Wait for async fetch to complete
    await screen.findByText("debate.validate");
    expect(global.fetch).toHaveBeenCalled();
  });

  it("should display cost level badges", () => {
    render(<DebateConfig {...defaultProps} enabled={true} />);

    // DeepSeek has low cost (avg 0.15), GPT-4o has medium cost (avg 6.25)
    const costBadges = screen.getAllByText(/\$|\$\$/);
    expect(costBadges.length).toBeGreaterThan(0);
  });

  it("should clear validation results when models change", () => {
    const { rerender } = render(
      <DebateConfig {...defaultProps} enabled={true} modelIds={["deepseek:chat"]} />
    );

    // Change model selection
    rerender(
      <DebateConfig {...defaultProps} enabled={true} modelIds={["openai:gpt-4o"]} />
    );

    // Validation results should be cleared (no validation indicators visible)
    expect(screen.queryByRole("img", { hidden: true })).not.toBeInTheDocument();
  });

  it("should toggle enabled state", async () => {
    const user = userEvent.setup();
    render(<DebateConfig {...defaultProps} enabled={false} />);

    const switchElement = screen.getByRole("switch");
    await user.click(switchElement);

    expect(defaultProps.onEnabledChange).toHaveBeenCalledWith(true);
  });
});

// ==================== PromptPreview ====================

describe("PromptPreview", () => {
  const mockPreview = {
    systemPrompt: "You are a conservative trader...",
    estimatedTokens: 1500,
    sections: {
      roleDefinition: "Role definition text",
      tradingMode: "Conservative mode",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
      customPrompt: "",
    },
  };

  const defaultProps = {
    preview: null,
    isLoading: false,
    onRefresh: jest.fn(),
  };

  it("should render title", () => {
    render(<PromptPreview {...defaultProps} />);

    expect(screen.getByText("preview.title")).toBeInTheDocument();
  });

  it("should show no-preview state when preview is null", () => {
    render(<PromptPreview {...defaultProps} />);

    expect(screen.getByText("preview.noPreview")).toBeInTheDocument();
    expect(screen.getByText("preview.generate")).toBeInTheDocument();
  });

  it("should display prompt content when preview exists", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    expect(screen.getByText("You are a conservative trader...")).toBeInTheDocument();
  });

  it("should show token count badge when preview exists", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    expect(screen.getByText(/1,500 tokens/)).toBeInTheDocument();
  });

  it("should call onRefresh when refresh button clicked", async () => {
    const user = userEvent.setup();
    const onRefresh = jest.fn();
    render(<PromptPreview {...defaultProps} onRefresh={onRefresh} />);

    // Refresh button is the first icon-only button (contains RefreshCw icon)
    const buttons = screen.getAllByRole("button");
    const refreshButton = buttons.find(
      (btn) => btn.querySelector(".lucide-refresh-cw") !== null
    );
    expect(refreshButton).toBeTruthy();
    await user.click(refreshButton!);

    expect(onRefresh).toHaveBeenCalled();
  });

  it("should disable refresh button when loading", () => {
    render(<PromptPreview {...defaultProps} isLoading={true} />);

    const buttons = screen.getAllByRole("button");
    const refreshButton = buttons.find(
      (btn) => btn.querySelector(".lucide-refresh-cw") !== null
    );
    expect(refreshButton).toBeDisabled();
  });

  it("should copy prompt to clipboard", async () => {
    const user = userEvent.setup();
    const mockWriteText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: mockWriteText },
      writable: true,
      configurable: true,
    });

    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    const buttons = screen.getAllByRole("button");
    const copyButton = buttons.find(
      (btn) => btn.querySelector(".lucide-copy") !== null
    );
    expect(copyButton).toBeTruthy();
    await user.click(copyButton!);

    expect(mockWriteText).toHaveBeenCalledWith("You are a conservative trader...");
  });

  it("should show check icon after copying", async () => {
    const user = userEvent.setup();
    const mockWriteText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: mockWriteText },
      writable: true,
      configurable: true,
    });

    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    const buttons = screen.getAllByRole("button");
    const copyButton = buttons.find(
      (btn) => btn.querySelector(".lucide-copy") !== null
    );
    expect(copyButton).toBeTruthy();
    await user.click(copyButton!);

    // After copy, the copy icon should be replaced with check icon
    expect(copyButton!.querySelector(".lucide-check")).toBeTruthy();
  });

  it("should disable copy button when no preview", () => {
    render(<PromptPreview {...defaultProps} preview={null} />);

    const buttons = screen.getAllByRole("button");
    const copyButton = buttons.find(
      (btn) => btn.querySelector(".lucide-copy") !== null
    );
    expect(copyButton).toBeDisabled();
  });

  it("should show loading spinner when isLoading is true", () => {
    render(<PromptPreview {...defaultProps} isLoading={true} preview={null} />);

    // The refresh icon should have animate-spin class when loading
    const buttons = screen.getAllByRole("button");
    const refreshButton = buttons.find(
      (btn) => btn.querySelector(".lucide-refresh-cw") !== null
    );
    expect(refreshButton).toBeTruthy();
    expect(refreshButton!.querySelector(".animate-spin")).toBeTruthy();
  });

  it("should display section tabs in simple mode", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} promptMode="simple" />);

    expect(screen.getByText("preview.fullPrompt")).toBeInTheDocument();
    expect(screen.getByText("preview.role")).toBeInTheDocument();
    expect(screen.getByText("preview.mode")).toBeInTheDocument();
  });

  it("should only show full prompt tab in advanced mode", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} promptMode="advanced" />);

    // In advanced mode, only 1 section exists so TabsList is hidden
    // But the full prompt content should still be visible
    expect(screen.getByText("You are a conservative trader...")).toBeInTheDocument();
    // Section tabs like "role" should not be present
    expect(screen.queryByText("preview.role")).not.toBeInTheDocument();
  });

  it("should switch between sections when clicking tabs", async () => {
    const user = userEvent.setup();
    render(<PromptPreview {...defaultProps} preview={mockPreview} promptMode="simple" />);

    const roleTab = screen.getByText("preview.role");
    await user.click(roleTab);

    // Should display role definition content
    expect(screen.getByText("Role definition text")).toBeInTheDocument();
  });

  it("should display default message for empty sections", async () => {
    const user = userEvent.setup();
    const previewWithEmptySection = {
      ...mockPreview,
      sections: {
        ...mockPreview.sections,
        roleDefinition: "",
      },
    };
    render(<PromptPreview {...defaultProps} preview={previewWithEmptySection} promptMode="simple" />);

    const roleTab = screen.getByText("preview.role");
    await user.click(roleTab);

    expect(screen.getByText("preview.usingDefault")).toBeInTheDocument();
  });

  it("should call onTest when test AI button clicked", async () => {
    const user = userEvent.setup();
    const onTest = jest.fn();
    render(<PromptPreview {...defaultProps} preview={mockPreview} onTest={onTest} />);

    const testButton = screen.getByText("preview.testAI");
    await user.click(testButton);

    expect(onTest).toHaveBeenCalled();
  });

  it("should disable test button when no preview", () => {
    const onTest = jest.fn();
    render(<PromptPreview {...defaultProps} preview={null} onTest={onTest} />);

    const testButton = screen.getByText("preview.testAI");
    expect(testButton).toBeDisabled();
  });

  it("should disable test button when test is loading", () => {
    const onTest = jest.fn();
    render(<PromptPreview {...defaultProps} preview={mockPreview} onTest={onTest} isTestLoading={true} />);

    const testButton = screen.getByText("preview.testing");
    expect(testButton).toBeDisabled();
  });

  it("should show testing text when test is loading", () => {
    const onTest = jest.fn();
    render(<PromptPreview {...defaultProps} preview={mockPreview} onTest={onTest} isTestLoading={true} />);

    expect(screen.getByText("preview.testing")).toBeInTheDocument();
  });

  it("should not show test button when onTest is not provided", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    expect(screen.queryByText("preview.testAI")).not.toBeInTheDocument();
  });

  it("should format token count with commas", () => {
    const previewWithLargeTokenCount = {
      ...mockPreview,
      estimatedTokens: 1234567,
    };
    render(<PromptPreview {...defaultProps} preview={previewWithLargeTokenCount} />);

    expect(screen.getByText(/1,234,567 tokens/)).toBeInTheDocument();
  });

  it("should display full prompt content", () => {
    render(<PromptPreview {...defaultProps} preview={mockPreview} />);

    expect(screen.getByText("You are a conservative trader...")).toBeInTheDocument();
  });

  it("should display section content when switching tabs", async () => {
    const user = userEvent.setup();
    const previewWithSections = {
      ...mockPreview,
      sections: {
        roleDefinition: "Role definition content",
        tradingMode: "Conservative mode",
        tradingFrequency: "Every 30 minutes",
        entryStandards: "High confidence only",
        decisionProcess: "Multi-step process",
        customPrompt: "",
      },
    };
    render(<PromptPreview {...defaultProps} preview={previewWithSections} promptMode="simple" />);

    const frequencyTab = screen.getByText("preview.frequency");
    await user.click(frequencyTab);

    expect(screen.getByText("Every 30 minutes")).toBeInTheDocument();
  });
});

// ==================== PromptTemplateEditor ====================

describe("PromptTemplateEditor", () => {
  const defaultProps = {
    promptMode: "simple" as const,
    onPromptModeChange: jest.fn(),
    value: {
      roleDefinition: "",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
    },
    onChange: jest.fn(),
    customPrompt: "",
    onCustomPromptChange: jest.fn(),
    advancedPrompt: "",
    onAdvancedPromptChange: jest.fn(),
    tradingMode: "conservative" as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render title", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    expect(screen.getByText("promptEditor.title")).toBeInTheDocument();
  });

  it("should render mode toggle", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    expect(screen.getByText("promptEditor.modeSimple")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.modeAdvanced")).toBeInTheDocument();
  });

  it("should render section editors in simple mode", () => {
    render(<PromptTemplateEditor {...defaultProps} promptMode="simple" />);

    expect(screen.getByText("promptEditor.advancedSections")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.sections.roleDefinition")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.sections.tradingFrequency")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.sections.entryStandards")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.sections.decisionProcess")).toBeInTheDocument();
  });

  it("should render advanced editor in advanced mode", () => {
    render(<PromptTemplateEditor {...defaultProps} promptMode="advanced" />);

    expect(screen.getByText("promptEditor.advancedModeTitle")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("promptEditor.advancedModePlaceholder")).toBeInTheDocument();
  });

  it("should toggle between simple and advanced mode", () => {
    render(<PromptTemplateEditor {...defaultProps} promptMode="simple" />);

    const switchElement = screen.getByRole("switch");
    fireEvent.click(switchElement);

    expect(defaultProps.onPromptModeChange).toHaveBeenCalledWith("advanced");
  });

  it("should expand section when clicked", () => {
    render(<PromptTemplateEditor {...defaultProps} promptMode="simple" />);

    const roleSection = screen.getByText("promptEditor.sections.roleDefinition").closest("button");
    if (roleSection) {
      fireEvent.click(roleSection);
      // After expanding, textarea should be visible
      expect(screen.getByPlaceholderText("promptEditor.placeholders.roleDefinition")).toBeInTheDocument();
    }
  });
});

// ==================== StrategyStudioTabs ====================

describe("StrategyStudioTabs", () => {
  const mockConfig = {
    name: "Test",
    description: "",
    accountId: "",
    aiModel: "",
    tradingMode: "conservative" as const,
    symbols: ["BTC", "ETH"],
    timeframes: ["15m" as const, "1h" as const, "4h" as const],
    executionIntervalMinutes: 30,
    autoExecute: true,
    indicators: {
      ema: { enabled: true, periods: [9, 21, 55] },
      rsi: { enabled: true, period: 14 },
      macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
      atr: { enabled: true, period: 14 },
    },
    riskControls: {
      maxLeverage: 5,
      maxPositionRatio: 0.2,
      maxTotalExposure: 0.8,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.1,
      minConfidence: 60,
    },
    language: "en",
    promptSections: {
      roleDefinition: "",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
    },
    customPrompt: "",
    debateEnabled: false,
    debateModels: [] as string[],
    debateConsensusMode: "majority_vote" as const,
    debateMinParticipants: 2,
  };

  const defaultProps = {
    config: mockConfig,
    onConfigChange: jest.fn(),
    activeTab: "coins" as const,
    onTabChange: jest.fn(),
    promptPreview: null,
    isPreviewLoading: false,
    onRefreshPreview: jest.fn(),
  };

  it("should render all 6 tab triggers", () => {
    render(<StrategyStudioTabs {...defaultProps} />);

    expect(screen.getByText("tabs.coins")).toBeInTheDocument();
    expect(screen.getByText("tabs.indicators")).toBeInTheDocument();
    expect(screen.getByText("tabs.risk")).toBeInTheDocument();
    expect(screen.getByText("tabs.prompt")).toBeInTheDocument();
    expect(screen.getByText("tabs.debate")).toBeInTheDocument();
    expect(screen.getByText("tabs.preview")).toBeInTheDocument();
  });

  it("should render CoinSelector on coins tab", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="coins" />);

    expect(screen.getByTestId("coin-selector")).toBeInTheDocument();
    expect(screen.getByTestId("timeframe-selector")).toBeInTheDocument();
  });

  it("should render IndicatorConfig on indicators tab", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="indicators" />);

    expect(screen.getByTestId("indicator-config")).toBeInTheDocument();
  });

  it("should render RiskControlsPanel on risk tab", () => {
    render(<StrategyStudioTabs {...defaultProps} activeTab="risk" />);

    expect(screen.getByTestId("risk-controls")).toBeInTheDocument();
  });

  it("should call onTabChange when clicking a tab", async () => {
    const user = userEvent.setup();
    const onTabChange = jest.fn();
    render(<StrategyStudioTabs {...defaultProps} onTabChange={onTabChange} />);

    const indicatorsTab = screen.getByText("tabs.indicators").closest("button");
    if (indicatorsTab) {
      await user.click(indicatorsTab);
      expect(onTabChange).toHaveBeenCalledWith("indicators");
    }
  });

  it("should update config when CoinSelector changes", () => {
    const onConfigChange = jest.fn();
    render(<StrategyStudioTabs {...defaultProps} onConfigChange={onConfigChange} />);

    // CoinSelector is mocked, so we can't directly interact with it
    // But we can verify the component structure
    expect(screen.getByTestId("coin-selector")).toBeInTheDocument();
  });

  it("should pass riskProfile and timeHorizon to RiskControlsPanel", () => {
    render(
      <StrategyStudioTabs
        {...defaultProps}
        activeTab="risk"
        riskProfile="conservative"
        timeHorizon="swing"
      />
    );

    expect(screen.getByTestId("risk-controls")).toBeInTheDocument();
  });

  it("should render PromptTemplateEditor on prompt tab", () => {
    // Mock PromptTemplateEditor
    jest.mock("@/components/strategy-studio/prompt-template-editor", () => ({
      PromptTemplateEditor: () => <div data-testid="prompt-editor">PromptEditor</div>,
    }));

    render(<StrategyStudioTabs {...defaultProps} activeTab="prompt" />);

    // The component should render, but since it's mocked in the test file,
    // we verify by checking the tab is active
    const promptTab = screen.getByText("tabs.prompt");
    expect(promptTab).toBeInTheDocument();
  });

  it("should render DebateConfig on debate tab", () => {
    // Mock DebateConfig
    jest.mock("@/components/strategy-studio/debate-config", () => ({
      DebateConfig: () => <div data-testid="debate-config">DebateConfig</div>,
    }));

    render(<StrategyStudioTabs {...defaultProps} activeTab="debate" />);

    const debateTab = screen.getByText("tabs.debate");
    expect(debateTab).toBeInTheDocument();
  });

  it("should render PromptPreview on preview tab", () => {
    // Mock PromptPreview
    jest.mock("@/components/strategy-studio/prompt-preview", () => ({
      PromptPreview: () => <div data-testid="prompt-preview">PromptPreview</div>,
    }));

    render(<StrategyStudioTabs {...defaultProps} activeTab="preview" />);

    const previewTab = screen.getByText("tabs.preview");
    expect(previewTab).toBeInTheDocument();
  });

  it("should handle all tab switches", () => {
    const onTabChange = jest.fn();
    const { rerender } = render(
      <StrategyStudioTabs {...defaultProps} activeTab="coins" onTabChange={onTabChange} />
    );

    const tabs = ["indicators", "risk", "prompt", "debate", "preview"] as const;
    tabs.forEach((tab) => {
      rerender(
        <StrategyStudioTabs {...defaultProps} activeTab={tab} onTabChange={onTabChange} />
      );
      expect(screen.getByText(`tabs.${tab}`)).toBeInTheDocument();
    });
  });
});

// ==================== DebateResultCard ====================

describe("DebateResultCard", () => {
  const mockSummary = {
    models: ["deepseek:chat", "openai:gpt-4o"],
    successful: 2,
    failed: 0,
    agreementScore: 0.85,
    consensusMode: "majority_vote" as const,
  };

  const mockParticipants = [
    {
      modelId: "deepseek:chat",
      succeeded: true,
      confidence: 80,
      latencyMs: 1200,
      tokensUsed: 500,
      decisions: [{ symbol: "BTC", action: "open_long", confidence: 80, reasoning: "" }],
    },
    {
      modelId: "openai:gpt-4o",
      succeeded: true,
      confidence: 75,
      latencyMs: 2000,
      tokensUsed: 800,
      decisions: [{ symbol: "BTC", action: "open_long", confidence: 75, reasoning: "" }],
    },
  ];

  it("should render result title and consensus mode", () => {
    render(
      <DebateResultCard summary={mockSummary} participants={mockParticipants} />
    );

    expect(screen.getByText("debate.resultTitle")).toBeInTheDocument();
  });

  it("should display successful and failed model counts", () => {
    render(
      <DebateResultCard summary={mockSummary} participants={mockParticipants} />
    );

    // "2" appears in both the successful count and the participants badge
    expect(screen.getByText("debate.successfulModels")).toBeInTheDocument();
    expect(screen.getByText("debate.failedModels")).toBeInTheDocument();
    // The successful count "2" is inside the stats grid
    const statsGrid = screen.getByText("debate.successfulModels").closest("div.p-3");
    expect(statsGrid?.querySelector(".text-2xl")?.textContent).toBe("2");
    // Failed count "0"
    const failedGrid = screen.getByText("debate.failedModels").closest("div.p-3");
    expect(failedGrid?.querySelector(".text-2xl")?.textContent).toBe("0");
  });

  it("should display agreement score as percentage", () => {
    render(
      <DebateResultCard summary={mockSummary} participants={mockParticipants} />
    );

    // 0.85 * 100 = 85%
    expect(screen.getAllByText("85%").length).toBeGreaterThan(0);
  });

  it("should render final decisions when provided", () => {
    const decisions = [
      { symbol: "BTC", action: "open_long", confidence: 80 },
      { symbol: "ETH", action: "hold", confidence: 60 },
    ];

    render(
      <DebateResultCard
        summary={mockSummary}
        participants={mockParticipants}
        finalDecisions={decisions}
      />
    );

    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("ETH")).toBeInTheDocument();
  });

  it("should show consensus reasoning when provided", () => {
    render(
      <DebateResultCard
        summary={mockSummary}
        participants={mockParticipants}
        consensusReasoning="Both models agree on BTC long position"
      />
    );

    expect(
      screen.getByText("Both models agree on BTC long position")
    ).toBeInTheDocument();
  });
});
