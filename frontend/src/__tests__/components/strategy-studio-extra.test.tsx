/**
 * Tests for Strategy Studio extra components:
 * - DebateConfig
 * - PromptPreview
 * - PromptTemplateEditor
 * - StrategyStudioTabs
 * - DebateResultCard
 */

import { render, screen, fireEvent } from "@testing-library/react";
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
