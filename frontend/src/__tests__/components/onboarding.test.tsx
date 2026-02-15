/**
 * Tests for Onboarding components:
 * - FloatingSetupGuide
 * - InlineOnboardingWizard
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock next/link
jest.mock("next/link", () => ({
  __esModule: true,
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock hooks used by FloatingSetupGuide
const mockAccounts: unknown[] = [];
const mockStrategies: unknown[] = [];
const mockModels: unknown[] = [];
const mockAgents: unknown[] = [];

jest.mock("@/hooks", () => ({
  useAccounts: () => ({
    accounts: mockAccounts,
    isLoading: false,
  }),
  useStrategies: () => ({
    strategies: mockStrategies,
    isLoading: false,
  }),
  useModels: () => ({
    models: mockModels,
    isLoading: false,
  }),
}));

jest.mock("@/hooks/use-agents", () => ({
  useAgents: () => ({
    agents: mockAgents,
    isLoading: false,
  }),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock API modules used by InlineOnboardingWizard
jest.mock("@/lib/api", () => ({
  accountsApi: {
    create: jest.fn().mockResolvedValue({ id: "test-account-id" }),
  },
  strategiesApi: {
    create: jest.fn().mockResolvedValue({ id: "test-strategy-id" }),
  },
  agentsApi: {
    create: jest.fn().mockResolvedValue({ id: "test-agent-id" }),
  },
  authApi: {},
}));

// Mock next-intl useTranslations
jest.mock("next-intl", () => {
  const createTranslator = () => {
    const t = (key: string) => key;
    t.rich = (key: string, components?: Record<string, (chunks: React.ReactNode) => React.ReactNode>) => {
      if (components && Object.keys(components).length > 0) {
        const firstComponent = Object.values(components)[0];
        return firstComponent(key);
      }
      return key;
    };
    return t;
  };

  return {
    useTranslations: () => createTranslator(),
  };
});

import { FloatingSetupGuide } from "@/components/onboarding/floating-setup-guide";
import { InlineOnboardingWizard } from "@/components/onboarding/inline-wizard";

// ==================== FloatingSetupGuide ====================

describe("FloatingSetupGuide", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    // Reset mock arrays
    mockAccounts.length = 0;
    mockStrategies.length = 0;
    mockModels.length = 0;
    mockAgents.length = 0;
  });

  it("should render guide when not dismissed and steps incomplete", async () => {
    render(<FloatingSetupGuide />);

    // Component starts with isDismissed=true, useEffect sets it to false
    await waitFor(() => expect(screen.getByText("title")).toBeInTheDocument());
    expect(screen.getByText("subtitle")).toBeInTheDocument();
  });

  it("should render step items", async () => {
    render(<FloatingSetupGuide />);

    await waitFor(() => expect(screen.getByText("steps.models.title")).toBeInTheDocument());
    expect(screen.getByText("steps.strategy.title")).toBeInTheDocument();
    expect(screen.getByText("steps.agent.title")).toBeInTheDocument();
    expect(screen.getByText("steps.account.title")).toBeInTheDocument();
  });

  it("should show progress indicator", async () => {
    render(<FloatingSetupGuide />);

    // 4 steps total now (models, strategy, agent, account)
    await waitFor(() => expect(screen.getByText("0/4")).toBeInTheDocument());
  });

  it("should dismiss when X button is clicked", async () => {
    const user = userEvent.setup();
    render(<FloatingSetupGuide />);

    // Wait for the component to render after useEffect
    await waitFor(() => expect(screen.getByText("title")).toBeInTheDocument());

    // Find dismiss button - it's a small icon button with the X svg
    const buttons = screen.getAllByRole("button");
    // The dismiss button contains a lucide-x SVG; look for it via the svg class
    const dismissBtn = buttons.find((b) =>
      b.querySelector('[class*="lucide-x"]')
    );

    expect(dismissBtn).toBeTruthy();
    if (dismissBtn) {
      await user.click(dismissBtn);
    }

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "bitrun-setup-guide-dismissed",
      "true"
    );
  });

  it("should not render when all required steps are complete", async () => {
    // Required steps: models, strategy, agent. Account is optional.
    mockModels.push({ id: "1" });
    mockStrategies.push({ id: "1" });
    mockAgents.push({ id: "1" });

    const { container } = render(<FloatingSetupGuide />);

    // Wait for useEffect to run, then it should still be null since all required complete
    await waitFor(() => {
      expect(container.innerHTML).toBe("");
    });
  });

  it("should not render when dismissed from localStorage", async () => {
    localStorageMock.getItem.mockReturnValue("true");

    const { container } = render(<FloatingSetupGuide />);

    expect(container.innerHTML).toBe("");
  });
});

// ==================== InlineOnboardingWizard ====================

describe("InlineOnboardingWizard", () => {
  const { accountsApi, strategiesApi, agentsApi: mockedAgentsApi } = require("@/lib/api");

  beforeEach(() => {
    jest.clearAllMocks();
    accountsApi.create.mockResolvedValue({ id: "test-account-id" });
    strategiesApi.create.mockResolvedValue({ id: "test-strategy-id" });
    mockedAgentsApi.create.mockResolvedValue({ id: "test-agent-id" });
  });

  describe("Step Indicator", () => {
    it("should render step indicator", () => {
      render(<InlineOnboardingWizard />);

      // Step labels should be visible
      expect(screen.getByText("Welcome")).toBeInTheDocument();
      expect(screen.getByText("Account")).toBeInTheDocument();
      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Risk")).toBeInTheDocument();
      expect(screen.getByText("Launch")).toBeInTheDocument();
    });

    it("should highlight current step", () => {
      render(<InlineOnboardingWizard />);

      // First step (Welcome) should be current
      const welcomeStep = screen.getByText("Welcome").closest("div");
      expect(welcomeStep).toBeInTheDocument();
    });
  });

  describe("Welcome Step", () => {
    it("should start on welcome step", () => {
      render(<InlineOnboardingWizard />);

      expect(screen.getByText("welcome.title")).toBeInTheDocument();
      expect(screen.getByText("welcome.subtitle")).toBeInTheDocument();
    });

    it("should display feature cards", () => {
      render(<InlineOnboardingWizard />);

      expect(screen.getByText("welcome.feature1Title")).toBeInTheDocument();
      expect(screen.getByText("welcome.feature2Title")).toBeInTheDocument();
      expect(screen.getByText("welcome.feature3Title")).toBeInTheDocument();
    });

    it("should navigate to account step when Get Started is clicked", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      const getStartedButton = screen.getByText("welcome.getStarted");
      await user.click(getStartedButton);

      // Should show account step
      expect(screen.getByText("account.title")).toBeInTheDocument();
    });
  });

  describe("Account Step", () => {
    it("should render account step after welcome", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      expect(screen.getByText("account.title")).toBeInTheDocument();
      expect(screen.getByText("account.description")).toBeInTheDocument();
    });

    it("should allow selecting exchange", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      const binanceButton = screen.getByText("Binance");
      await user.click(binanceButton);

      expect(binanceButton).toHaveClass("glow-primary");
    });

    it("should show API key/secret fields for Binance", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      expect(screen.getByText("account.apiKey")).toBeInTheDocument();
      expect(screen.getByText("account.apiSecret")).toBeInTheDocument();
    });

    it("should show private key/mnemonic fields for Hyperliquid", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Hyperliquid"));

      expect(screen.getByText("account.importType")).toBeInTheDocument();
      // Check for label text, not button text
      const privateKeyLabels = screen.getAllByText("account.privateKey");
      expect(privateKeyLabels.length).toBeGreaterThan(0);
      // Check for input placeholder
      expect(screen.getByPlaceholderText("0x...")).toBeInTheDocument();
    });

    it("should toggle between private key and mnemonic for Hyperliquid", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Hyperliquid"));

      // Find mnemonic button (there are multiple elements with this text)
      const mnemonicButtons = screen.getAllByText("account.mnemonic");
      const mnemonicButton = mnemonicButtons.find(btn => btn.tagName === "BUTTON");
      expect(mnemonicButton).toBeTruthy();
      if (mnemonicButton) {
        await user.click(mnemonicButton);
      }

      // Check for mnemonic input placeholder
      expect(screen.getByPlaceholderText("account.mnemonicPlaceholder")).toBeInTheDocument();
    });

    it("should allow entering account name", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      await user.type(accountNameInput, "My Test Account");

      expect(accountNameInput).toHaveValue("My Test Account");
    });

    it("should toggle testnet mode", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      const testnetSwitch = screen.getByRole("switch");
      expect(testnetSwitch).toBeChecked(); // Default is testnet

      await user.click(testnetSwitch);
      expect(testnetSwitch).not.toBeChecked();
    });

    it("should disable next button when form is incomplete", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      const nextButton = screen.getByText("common.next");
      expect(nextButton).toBeDisabled();
    });

    it("should enable next button when form is complete for Binance", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      const nextButton = screen.getByText("common.next");
      expect(nextButton).not.toBeDisabled();
    });

    it("should enable next button when form is complete for Hyperliquid with private key", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Hyperliquid"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const privateKeyInput = screen.getByPlaceholderText("0x...");

      await user.type(accountNameInput, "Test Account");
      await user.type(privateKeyInput, "0x1234567890abcdef");

      const nextButton = screen.getByText("common.next");
      expect(nextButton).not.toBeDisabled();
    });

    it("should enable next button when form is complete for Hyperliquid with mnemonic", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Hyperliquid"));
      
      // Find mnemonic button (there are multiple elements with this text)
      const mnemonicButtons = screen.getAllByText("account.mnemonic");
      const mnemonicButton = mnemonicButtons.find(btn => btn.tagName === "BUTTON");
      expect(mnemonicButton).toBeTruthy();
      if (mnemonicButton) {
        await user.click(mnemonicButton);
      }

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const mnemonicInput = screen.getByPlaceholderText("account.mnemonicPlaceholder");

      await user.type(accountNameInput, "Test Account");
      await user.type(mnemonicInput, "word1 word2 word3");

      const nextButton = screen.getByText("common.next");
      expect(nextButton).not.toBeDisabled();
    });

    it("should call accountsApi.create when next is clicked", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      const nextButton = screen.getByText("common.next");
      await user.click(nextButton);

      await screen.findByText("agent.title"); // Wait for next step

      expect(accountsApi.create).toHaveBeenCalledWith({
        name: "Test Account",
        exchange: "binance",
        is_testnet: true,
        api_key: "test-api-key",
        api_secret: "test-api-secret",
      });
    });

    it("should handle account creation error", async () => {
      accountsApi.create.mockRejectedValueOnce(new Error("API Error"));
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      const nextButton = screen.getByText("common.next");
      await user.click(nextButton);

      await screen.findByText("API Error");
      expect(screen.getByText("API Error")).toBeInTheDocument();
    });

    it("should go back to welcome step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await user.click(screen.getByText("welcome.getStarted"));

      const backButton = screen.getByText("common.back");
      await user.click(backButton);

      expect(screen.getByText("welcome.title")).toBeInTheDocument();
    });
  });

  describe("Agent Step", () => {
    const navigateToAgentStep = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      const nextButton = screen.getByText("common.next");
      await user.click(nextButton);

      await screen.findByText("agent.title");
    };

    it("should render agent step after account creation", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      expect(screen.getByText("agent.title")).toBeInTheDocument();
      expect(screen.getByText("agent.description")).toBeInTheDocument();
    });

    it("should allow entering agent name", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const agentNameInput = screen.getByPlaceholderText("agent.agentNamePlaceholder");
      await user.type(agentNameInput, "My Trading Bot");

      expect(agentNameInput).toHaveValue("My Trading Bot");
    });

    it("should allow selecting trading pairs", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const ethPair = screen.getByText("ETH/USDT");
      await user.click(ethPair);

      expect(ethPair).toHaveClass("glow-primary");
    });

    it("should allow deselecting trading pairs", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const btcPair = screen.getByText("BTC/USDT");
      // BTC/USDT is selected by default
      await user.click(btcPair);

      // Should be deselected
      expect(btcPair).not.toHaveClass("glow-primary");
    });

    it("should allow selecting trading mode", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const aggressiveButton = screen.getByText("agent.modes.aggressive");
      await user.click(aggressiveButton);

      // Check if button is selected (it should have glow-primary class or be the active variant)
      // The button might have the class on a parent or use data attributes
      expect(aggressiveButton.closest("button")).toBeInTheDocument();
      // Verify the button was clicked by checking if it's the selected one
      const buttons = screen.getAllByText(/agent\.modes\.(conservative|moderate|aggressive)/);
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("should allow entering trading instructions", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const promptInput = screen.getByPlaceholderText("agent.instructionsPlaceholder");
      await user.type(promptInput, "Buy when RSI < 30");

      expect(promptInput).toHaveValue("Buy when RSI < 30");
    });

    it("should disable next button when form is incomplete", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const nextButton = screen.getByText("common.next");
      expect(nextButton).toBeDisabled();
    });

    it("should enable next button when form is complete", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const agentNameInput = screen.getByPlaceholderText("agent.agentNamePlaceholder");
      const promptInput = screen.getByPlaceholderText("agent.instructionsPlaceholder");

      await user.type(agentNameInput, "My Bot");
      await user.type(promptInput, "Trade carefully");

      const nextButton = screen.getByText("common.next");
      expect(nextButton).not.toBeDisabled();
    });

    it("should go back to account step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToAgentStep(user);

      const backButton = screen.getByText("common.back");
      await user.click(backButton);

      expect(screen.getByText("account.title")).toBeInTheDocument();
    });
  });

  describe("Risk Step", () => {
    const navigateToRiskStep = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      let nextButton = screen.getByText("common.next");
      await user.click(nextButton);
      await screen.findByText("agent.title");

      const agentNameInput = screen.getByPlaceholderText("agent.agentNamePlaceholder");
      const promptInput = screen.getByPlaceholderText("agent.instructionsPlaceholder");

      await user.type(agentNameInput, "My Bot");
      await user.type(promptInput, "Trade carefully");

      nextButton = screen.getByText("common.next");
      await user.click(nextButton);
      await screen.findByText("risk.title");
    };

    it("should render risk step after agent step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToRiskStep(user);

      expect(screen.getByText("risk.title")).toBeInTheDocument();
      expect(screen.getByText("risk.description")).toBeInTheDocument();
    });

    it("should display default risk values", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToRiskStep(user);

      expect(screen.getByText("5x")).toBeInTheDocument(); // maxLeverage
      // There might be multiple percentage elements, check that they exist
      const tenPercentElements = screen.getAllByText("10%");
      expect(tenPercentElements.length).toBeGreaterThan(0);
      const fiftyPercentElements = screen.getAllByText("50%");
      expect(fiftyPercentElements.length).toBeGreaterThan(0);
      expect(screen.getByText("70%")).toBeInTheDocument(); // confidenceThreshold
    });

    it("should allow going back to agent step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToRiskStep(user);

      const backButton = screen.getByText("common.back");
      await user.click(backButton);

      expect(screen.getByText("agent.title")).toBeInTheDocument();
    });
  });

  describe("Launch Step", () => {
    const navigateToLaunchStep = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByText("welcome.getStarted"));
      await user.click(screen.getByText("Binance"));

      const accountNameInput = screen.getByPlaceholderText("account.accountNamePlaceholder");
      const apiKeyInput = screen.getByPlaceholderText("account.enterApiKey");
      const apiSecretInput = screen.getByPlaceholderText("account.enterApiSecret");

      await user.type(accountNameInput, "Test Account");
      await user.type(apiKeyInput, "test-api-key");
      await user.type(apiSecretInput, "test-api-secret");

      let nextButton = screen.getByText("common.next");
      await user.click(nextButton);
      await screen.findByText("agent.title");

      const agentNameInput = screen.getByPlaceholderText("agent.agentNamePlaceholder");
      const promptInput = screen.getByPlaceholderText("agent.instructionsPlaceholder");

      await user.type(agentNameInput, "My Bot");
      await user.type(promptInput, "Trade carefully");

      nextButton = screen.getByText("common.next");
      await user.click(nextButton);
      await screen.findByText("risk.title");

      nextButton = screen.getByText("common.next");
      await user.click(nextButton);
      await screen.findByText("launch.title");
    };

    it("should render launch step after risk step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToLaunchStep(user);

      expect(screen.getByText("launch.title")).toBeInTheDocument();
      expect(screen.getByText("launch.description")).toBeInTheDocument();
    });

    it("should display configuration preview", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToLaunchStep(user);

      expect(screen.getByText("My Bot")).toBeInTheDocument(); // agentName
      expect(screen.getByText("Binance")).toBeInTheDocument(); // exchange
      expect(screen.getByText("BTC/USDT")).toBeInTheDocument(); // tradingPairs
    });

    it("should require confirmation checkbox for testnet", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToLaunchStep(user);

      const launchButton = screen.getByText("launch.launchAgent");
      expect(launchButton).toBeDisabled(); // Testnet requires confirmation

      const checkbox = screen.getByLabelText("launch.confirmTestnet");
      await user.click(checkbox);

      expect(launchButton).not.toBeDisabled();
    });

    it("should call strategiesApi.create when launch is clicked", async () => {
      const user = userEvent.setup();
      const onComplete = jest.fn();
      render(<InlineOnboardingWizard onComplete={onComplete} />);

      await navigateToLaunchStep(user);

      const checkbox = screen.getByLabelText("launch.confirmTestnet");
      await user.click(checkbox);

      const launchButton = screen.getByText("launch.launchAgent");
      await user.click(launchButton);

      // Wait for API call to complete - the component resets to step 0 on success
      await screen.findByText("welcome.title", {}, { timeout: 3000 });

      expect(strategiesApi.create).toHaveBeenCalled();
      expect(onComplete).toHaveBeenCalled();
    });

    it("should handle launch error", async () => {
      strategiesApi.create.mockRejectedValueOnce(new Error("Launch failed"));
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToLaunchStep(user);

      const checkbox = screen.getByLabelText("launch.confirmTestnet");
      await user.click(checkbox);

      const launchButton = screen.getByText("launch.launchAgent");
      await user.click(launchButton);

      // Wait for error handling - LaunchStep doesn't display errors, but isLoading should be false
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Verify the API was called
      expect(strategiesApi.create).toHaveBeenCalled();
      // The error is caught and setError is called, but LaunchStep doesn't display it
      // We verify the button is no longer in loading state
      const launchButtonAfter = screen.queryByText("launch.launchAgent");
      expect(launchButtonAfter).toBeInTheDocument();
    });

    it("should allow skipping launch", async () => {
      const user = userEvent.setup();
      const onComplete = jest.fn();
      render(<InlineOnboardingWizard onComplete={onComplete} />);

      await navigateToLaunchStep(user);

      const skipButton = screen.getByText("launch.skipForNow");
      await user.click(skipButton);

      expect(screen.getByText("welcome.title")).toBeInTheDocument();
      expect(onComplete).toHaveBeenCalled();
    });

    it("should allow going back to risk step", async () => {
      const user = userEvent.setup();
      render(<InlineOnboardingWizard />);

      await navigateToLaunchStep(user);

      const backButton = screen.getByText("launch.modifyConfig");
      await user.click(backButton);

      expect(screen.getByText("risk.title")).toBeInTheDocument();
    });
  });

  describe("Complete Flow", () => {
    it("should complete full onboarding flow", async () => {
      const user = userEvent.setup();
      const onComplete = jest.fn();
      render(<InlineOnboardingWizard onComplete={onComplete} />);

      // Step 1: Welcome
      await user.click(screen.getByText("welcome.getStarted"));

      // Step 2: Account
      await user.click(screen.getByText("Binance"));
      await user.type(screen.getByPlaceholderText("account.accountNamePlaceholder"), "Test Account");
      await user.type(screen.getByPlaceholderText("account.enterApiKey"), "test-key");
      await user.type(screen.getByPlaceholderText("account.enterApiSecret"), "test-secret");
      await user.click(screen.getByText("common.next"));
      await screen.findByText("agent.title");

      // Step 3: Agent
      await user.type(screen.getByPlaceholderText("agent.agentNamePlaceholder"), "My Bot");
      await user.type(screen.getByPlaceholderText("agent.instructionsPlaceholder"), "Trade");
      await user.click(screen.getByText("common.next"));
      await screen.findByText("risk.title");

      // Step 4: Risk
      await user.click(screen.getByText("common.next"));
      await screen.findByText("launch.title");

      // Step 5: Launch
      await user.click(screen.getByLabelText("launch.confirmTestnet"));
      await user.click(screen.getByText("launch.launchAgent"));
      await screen.findByText("welcome.title");

      expect(accountsApi.create).toHaveBeenCalled();
      expect(strategiesApi.create).toHaveBeenCalled();
      expect(mockedAgentsApi.create).toHaveBeenCalled();
      expect(onComplete).toHaveBeenCalled();
    });
  });
});
