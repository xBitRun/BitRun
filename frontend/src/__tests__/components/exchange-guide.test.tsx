/**
 * Tests for ExchangeGuide component
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { ExchangeGuide } from "@/components/accounts/exchange-guide";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      title: "API Setup Guide",
      titleCex: "API Setup Guide",
      titleDex: "Wallet Setup Guide",
      showGuide: "Show Guide",
      hideGuide: "Hide Guide",
      registerLink: "Register",
      officialDocs: "Official Docs",
      stepsTitle: "Setup Steps",
      permissionsTitle: "Required Permissions",
      securityTitle: "Security Tips",
      tipPassphrase: "Passphrase required",
      tipTestnet: "Use testnet first",
      tipSecret: "Keep your secret safe",
      // Binance
      "binance.step1": "Log in to Binance",
      "binance.step2": "Go to API Management",
      "binance.step3": "Create new API key",
      "binance.step4": "Set permissions",
      "binance.step5": "Complete verification",
      "binance.perm1": "Read",
      "binance.perm2": "Spot Trading",
      "binance.perm3": "Futures Trading",
      "binance.contractNote": "Contract note",
      "binance.ipWhitelist": "IP whitelist required",
      // Bybit
      "bybit.step1": "Log in to Bybit",
      "bybit.step2": "Go to API",
      "bybit.step3": "Create API key",
      "bybit.step4": "Set permissions",
      "bybit.step5": "Save your keys",
      "bybit.perm1": "Read",
      "bybit.perm2": "Trading",
      "bybit.perm3": "Positions",
      "bybit.proxyNote": "Proxy note",
      // OKX
      "okx.step1": "Log in to OKX",
      "okx.step2": "Go to API",
      "okx.step3": "Create API key",
      "okx.step4": "Set passphrase",
      "okx.step5": "Set permissions",
      "okx.step6": "Complete 2FA",
      "okx.perm1": "Read",
      "okx.perm2": "Trade",
      "okx.perm3": "Withdraw",
      "okx.passphraseNote": "Passphrase note",
      "okx.proxyNote": "Proxy note",
      // Hyperliquid
      "hyperliquid.title": "Hyperliquid Guide",
      "hyperliquid.privateKeyGuide": "Use your private key",
      "hyperliquid.mnemonicGuide": "Or use mnemonic",
      "hyperliquid.securityNote": "Security warning",
      "hyperliquid.fundingNote": "Funding info",
      // Bitget
      "bitget.step1": "Log in",
      "bitget.step2": "Create API",
      "bitget.step3": "Set permissions",
      "bitget.step4": "Save keys",
      "bitget.perm1": "Read",
      "bitget.perm2": "Trade",
      "bitget.perm3": "Positions",
      "bitget.passphraseNote": "Passphrase required",
      "bitget.note": "Important note",
      // KuCoin
      "kucoin.step1": "Log in",
      "kucoin.step2": "Create API",
      "kucoin.step3": "Set permissions",
      "kucoin.step4": "Save keys",
      "kucoin.perm1": "Read",
      "kucoin.perm2": "Trade",
      "kucoin.perm3": "Positions",
      "kucoin.passphraseNote": "Passphrase required",
      "kucoin.note": "Important note",
      // Gate
      "gate.step1": "Log in",
      "gate.step2": "Create API",
      "gate.step3": "Set permissions",
      "gate.step4": "Save keys",
      "gate.perm1": "Read",
      "gate.perm2": "Trade",
      "gate.perm3": "Withdraw",
      "gate.passphraseNote": "Passphrase required",
      "gate.note": "Important note",
    };
    return translations[key] || key;
  },
}));

// Mock ServerIPBadge
jest.mock("@/components/accounts/server-ip-badge", () => ({
  ServerIPBadge: () => <div data-testid="server-ip-badge">Server IP</div>,
}));

describe("ExchangeGuide", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render collapsed by default", () => {
    render(<ExchangeGuide exchange="binance" />);

    expect(screen.getByText("API Setup Guide")).toBeInTheDocument();
    expect(screen.getByText("Show Guide")).toBeInTheDocument();
    expect(screen.queryByText("Setup Steps")).not.toBeInTheDocument();
  });

  it("should expand on click", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Hide Guide")).toBeInTheDocument();
    expect(screen.getByText("Setup Steps")).toBeInTheDocument();
  });

  it("should collapse on second click", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);
    fireEvent.click(header!);

    expect(screen.getByText("Show Guide")).toBeInTheDocument();
    expect(screen.queryByText("Setup Steps")).not.toBeInTheDocument();
  });

  it("should render register link for Binance", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    const registerLink = screen.getByText("Register").closest("a");
    expect(registerLink).toHaveAttribute("href", "https://www.binance.com");
  });

  it("should render API docs link for Binance", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    const docsLink = screen.getByText("Official Docs").closest("a");
    expect(docsLink?.href).toContain("binance.com");
  });

  it("should render Binance-specific guide", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Log in to Binance")).toBeInTheDocument();
    expect(screen.getByText("Spot Trading")).toBeInTheDocument();
  });

  it("should render Bybit-specific guide", () => {
    render(<ExchangeGuide exchange="bybit" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Log in to Bybit")).toBeInTheDocument();
    expect(screen.getByText("Trading")).toBeInTheDocument();
  });

  it("should render OKX-specific guide", () => {
    render(<ExchangeGuide exchange="okx" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Log in to OKX")).toBeInTheDocument();
    expect(screen.getByText("Trade")).toBeInTheDocument();
  });

  it("should render Hyperliquid-specific guide", () => {
    render(<ExchangeGuide exchange="hyperliquid" />);

    // Hyperliquid is a DEX, uses titleDex
    const header = screen.getByText("Wallet Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Hyperliquid Guide")).toBeInTheDocument();
    expect(screen.getByText("Use your private key")).toBeInTheDocument();
    expect(screen.getByText("Or use mnemonic")).toBeInTheDocument();
  });

  it("should render Bitget-specific guide", () => {
    render(<ExchangeGuide exchange="bitget" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Passphrase required")).toBeInTheDocument();
    expect(screen.getByText("Important note")).toBeInTheDocument();
  });

  it("should render KuCoin-specific guide", () => {
    render(<ExchangeGuide exchange="kucoin" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Passphrase required")).toBeInTheDocument();
  });

  it("should render Gate-specific guide", () => {
    render(<ExchangeGuide exchange="gate" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    // Gate doesn't have passphrase note
    expect(screen.getByText("Important note")).toBeInTheDocument();
  });

  it("should render ServerIPBadge for CEX exchanges", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByTestId("server-ip-badge")).toBeInTheDocument();
  });

  it("should not render API docs link for Hyperliquid", () => {
    render(<ExchangeGuide exchange="hyperliquid" />);

    // Hyperliquid is a DEX, so it uses titleDex
    const header = screen.getByText("Wallet Setup Guide").closest("button");
    fireEvent.click(header!);

    // Hyperliquid has no API docs
    expect(screen.queryByText("Official Docs")).not.toBeInTheDocument();
  });

  it("should render step items with numbers", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("should render permission items with check icons", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Required Permissions")).toBeInTheDocument();
    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(screen.getByText("Spot Trading")).toBeInTheDocument();
  });

  it("should render with custom className", () => {
    const { container } = render(
      <ExchangeGuide exchange="binance" className="custom-class" />
    );

    expect(container.querySelector(".custom-class")).toBeInTheDocument();
  });

  it("should have external links open in new tab", () => {
    render(<ExchangeGuide exchange="binance" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    const registerLink = screen.getByText("Register").closest("a");
    expect(registerLink).toHaveAttribute("target", "_blank");
    expect(registerLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("should render OKX with 6 steps", () => {
    render(<ExchangeGuide exchange="okx" />);

    const header = screen.getByText("API Setup Guide").closest("button");
    fireEvent.click(header!);

    expect(screen.getByText("Complete 2FA")).toBeInTheDocument();
  });
});
