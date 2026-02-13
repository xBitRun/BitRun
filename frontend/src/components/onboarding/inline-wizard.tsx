"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Bot,
  Wallet,
  Shield,
  Rocket,
  FileText,
  Zap,
  BarChart3,
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Exchange options
const EXCHANGES = [
  { id: "hyperliquid", name: "Hyperliquid", requiresPrivateKey: true },
  { id: "binance", name: "Binance", requiresPrivateKey: false },
  { id: "bybit", name: "Bybit", requiresPrivateKey: false },
];

// Trading modes
const TRADING_MODES = ["conservative", "moderate", "aggressive"] as const;

interface OnboardingState {
  // Step 2: Account
  exchange: string;
  accountName: string;
  apiKey: string;
  apiSecret: string;
  privateKey: string;
  mnemonic: string;
  hlImportType: "privateKey" | "mnemonic";
  isTestnet: boolean;
  // Step 3: Agent
  agentName: string;
  tradingPairs: string[];
  tradingMode: (typeof TRADING_MODES)[number];
  prompt: string;
  // Step 4: Risk
  maxLeverage: number;
  maxPositionSize: number;
  maxExposure: number;
  confidenceThreshold: number;
}

const initialState: OnboardingState = {
  exchange: "",
  accountName: "",
  apiKey: "",
  apiSecret: "",
  privateKey: "",
  mnemonic: "",
  hlImportType: "privateKey",
  isTestnet: true,
  agentName: "",
  tradingPairs: ["BTC/USDT"],
  tradingMode: "moderate",
  prompt: "",
  maxLeverage: 5,
  maxPositionSize: 10,
  maxExposure: 50,
  confidenceThreshold: 70,
};

// Progress indicator component - horizontal stepper
function StepIndicator({ currentStep }: { currentStep: number }) {
  const steps = [
    { icon: Zap, label: "Welcome" },
    { icon: Wallet, label: "Account" },
    { icon: Bot, label: "Agent" },
    { icon: Shield, label: "Risk" },
    { icon: Rocket, label: "Launch" },
  ];

  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        const Icon = step.icon;

        return (
          <div key={index} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-full transition-all",
                  isCompleted
                    ? "bg-primary text-primary-foreground"
                    : isCurrent
                    ? "bg-primary/20 text-primary border-2 border-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs mt-1.5 font-medium",
                  isCurrent ? "text-primary" : "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "w-12 lg:w-20 h-0.5 mx-2 mb-5",
                  index < currentStep ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Step 1: Welcome
function WelcomeStep({
  t,
  onNext,
}: {
  t: ReturnType<typeof useTranslations>;
  onNext: () => void;
}) {
  return (
    <div className="flex flex-col items-center text-center py-8 max-w-2xl mx-auto">
      <div className="p-6 rounded-full bg-primary/10 mb-6">
        <Bot className="w-16 h-16 text-primary" />
      </div>
      <h1 className="text-3xl font-bold mb-3">{t("welcome.title")}</h1>
      <p className="text-muted-foreground mb-8 text-lg max-w-lg">
        {t("welcome.subtitle")}
      </p>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 w-full">
        <Card className="bg-muted/30 border-border/50">
          <CardContent className="flex flex-col items-center p-6">
            <FileText className="w-10 h-10 text-primary mb-3" />
            <p className="font-semibold">{t("welcome.feature1Title")}</p>
            <p className="text-sm text-muted-foreground text-center mt-1">
              {t("welcome.feature1Desc")}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-muted/30 border-border/50">
          <CardContent className="flex flex-col items-center p-6">
            <Shield className="w-10 h-10 text-primary mb-3" />
            <p className="font-semibold">{t("welcome.feature2Title")}</p>
            <p className="text-sm text-muted-foreground text-center mt-1">
              {t("welcome.feature2Desc")}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-muted/30 border-border/50">
          <CardContent className="flex flex-col items-center p-6">
            <BarChart3 className="w-10 h-10 text-primary mb-3" />
            <p className="font-semibold">{t("welcome.feature3Title")}</p>
            <p className="text-sm text-muted-foreground text-center mt-1">
              {t("welcome.feature3Desc")}
            </p>
          </CardContent>
        </Card>
      </div>

      <Button size="lg" className="glow-primary text-lg px-8" onClick={onNext}>
        {t("welcome.getStarted")}
        <ArrowRight className="w-5 h-5 ml-2" />
      </Button>
    </div>
  );
}

// Step 2: Connect Account
function AccountStep({
  t,
  state,
  onChange,
  onNext,
  onBack,
  isLoading,
  error,
}: {
  t: ReturnType<typeof useTranslations>;
  state: OnboardingState;
  onChange: (updates: Partial<OnboardingState>) => void;
  onNext: () => void;
  onBack: () => void;
  isLoading: boolean;
  error: string | null;
}) {
  const selectedExchange = EXCHANGES.find((e) => e.id === state.exchange);

  const canProceed =
    state.exchange &&
    state.accountName &&
    (selectedExchange?.requiresPrivateKey
      ? state.hlImportType === "mnemonic"
        ? state.mnemonic
        : state.privateKey
      : state.apiKey && state.apiSecret);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="mx-auto p-4 rounded-full bg-primary/10 mb-3 w-fit">
          <Wallet className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">{t("account.title")}</h2>
        <p className="text-muted-foreground">{t("account.description")}</p>
      </div>

      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="p-6 space-y-5">
          {/* Exchange Selection */}
          <div className="space-y-2">
            <Label>{t("account.selectExchange")}</Label>
            <div className="grid grid-cols-3 gap-3">
              {EXCHANGES.map((exchange) => (
                <Button
                  key={exchange.id}
                  type="button"
                  variant={state.exchange === exchange.id ? "default" : "outline"}
                  className={cn(
                    "h-auto py-4",
                    state.exchange === exchange.id && "glow-primary"
                  )}
                  onClick={() => onChange({ exchange: exchange.id })}
                >
                  {exchange.name}
                </Button>
              ))}
            </div>
          </div>

          {/* Account Name */}
          <div className="space-y-2">
            <Label>{t("account.accountName")}</Label>
            <Input
              placeholder={t("account.accountNamePlaceholder")}
              value={state.accountName}
              onChange={(e) => onChange({ accountName: e.target.value })}
              className="bg-muted/50"
            />
          </div>

          {/* Testnet Toggle */}
          <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
            <div>
              <p className="font-medium">{t("account.testnetMode")}</p>
              <p className="text-sm text-muted-foreground">
                {t("account.testnetDescription")}
              </p>
            </div>
            <Switch
              checked={state.isTestnet}
              onCheckedChange={(checked) => onChange({ isTestnet: checked })}
            />
          </div>

          {/* Credentials */}
          {state.exchange && (
            <>
              {selectedExchange?.requiresPrivateKey ? (
                <>
                  {/* Hyperliquid: Import Type Selection */}
                  <div className="space-y-2">
                    <Label>{t("account.importType")}</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <Button
                        type="button"
                        variant={
                          state.hlImportType === "privateKey" ? "default" : "outline"
                        }
                        className={cn(
                          "h-auto py-3",
                          state.hlImportType === "privateKey" && "glow-primary"
                        )}
                        onClick={() => onChange({ hlImportType: "privateKey" })}
                      >
                        {t("account.privateKey")}
                      </Button>
                      <Button
                        type="button"
                        variant={
                          state.hlImportType === "mnemonic" ? "default" : "outline"
                        }
                        className={cn(
                          "h-auto py-3",
                          state.hlImportType === "mnemonic" && "glow-primary"
                        )}
                        onClick={() => onChange({ hlImportType: "mnemonic" })}
                      >
                        {t("account.mnemonic")}
                      </Button>
                    </div>
                  </div>

                  {/* Private Key Input */}
                  {state.hlImportType === "privateKey" && (
                    <div className="space-y-2">
                      <Label>{t("account.privateKey")}</Label>
                      <Input
                        type="password"
                        placeholder="0x..."
                        value={state.privateKey}
                        onChange={(e) => onChange({ privateKey: e.target.value })}
                        className="bg-muted/50 font-mono"
                      />
                    </div>
                  )}

                  {/* Mnemonic Input */}
                  {state.hlImportType === "mnemonic" && (
                    <div className="space-y-2">
                      <Label>{t("account.mnemonic")}</Label>
                      <Input
                        type="password"
                        placeholder={t("account.mnemonicPlaceholder")}
                        value={state.mnemonic}
                        onChange={(e) => onChange({ mnemonic: e.target.value })}
                        className="bg-muted/50 font-mono"
                      />
                      <p className="text-xs text-muted-foreground">
                        {t("account.mnemonicHint")}
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label>{t("account.apiKey")}</Label>
                    <Input
                      type="password"
                      placeholder={t("account.enterApiKey")}
                      value={state.apiKey}
                      onChange={(e) => onChange({ apiKey: e.target.value })}
                      className="bg-muted/50 font-mono"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{t("account.apiSecret")}</Label>
                    <Input
                      type="password"
                      placeholder={t("account.enterApiSecret")}
                      value={state.apiSecret}
                      onChange={(e) => onChange({ apiSecret: e.target.value })}
                      className="bg-muted/50 font-mono"
                    />
                  </div>
                </>
              )}
            </>
          )}

          {/* Security Note */}
          <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary shrink-0" />
            <p className="text-sm text-muted-foreground">
              {t.rich("account.securityNote", {
                highlight: (chunks) => (
                  <span className="text-primary font-medium">{chunks}</span>
                ),
              })}
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/30 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-destructive" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={onBack} className="flex-1">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t("common.back")}
            </Button>
            <Button
              onClick={onNext}
              disabled={!canProceed || isLoading}
              className="flex-1 glow-primary"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              {t("common.next")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Step 3: Create Agent
function AgentStep({
  t,
  state,
  onChange,
  onNext,
  onBack,
}: {
  t: ReturnType<typeof useTranslations>;
  state: OnboardingState;
  onChange: (updates: Partial<OnboardingState>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const canProceed =
    state.agentName && state.tradingPairs.length > 0 && state.prompt;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="mx-auto p-4 rounded-full bg-primary/10 mb-3 w-fit">
          <Bot className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">{t("agent.title")}</h2>
        <p className="text-muted-foreground">{t("agent.description")}</p>
      </div>

      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="p-6 space-y-5">
          {/* Agent Name */}
          <div className="space-y-2">
            <Label>{t("agent.agentName")}</Label>
            <Input
              placeholder={t("agent.agentNamePlaceholder")}
              value={state.agentName}
              onChange={(e) => onChange({ agentName: e.target.value })}
              className="bg-muted/50"
            />
          </div>

          {/* Trading Pairs */}
          <div className="space-y-2">
            <Label>{t("agent.tradingPairs")}</Label>
            <div className="flex flex-wrap gap-2">
              {["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"].map((pair) => (
                <Badge
                  key={pair}
                  variant={state.tradingPairs.includes(pair) ? "default" : "outline"}
                  className={cn(
                    "cursor-pointer px-4 py-2 text-sm",
                    state.tradingPairs.includes(pair) && "glow-primary"
                  )}
                  onClick={() => {
                    const pairs = state.tradingPairs.includes(pair)
                      ? state.tradingPairs.filter((p) => p !== pair)
                      : [...state.tradingPairs, pair];
                    onChange({ tradingPairs: pairs });
                  }}
                >
                  {pair}
                </Badge>
              ))}
            </div>
          </div>

          {/* Trading Mode */}
          <div className="space-y-2">
            <Label>{t("agent.tradingMode")}</Label>
            <div className="grid grid-cols-3 gap-3">
              {TRADING_MODES.map((mode) => (
                <Button
                  key={mode}
                  type="button"
                  variant={state.tradingMode === mode ? "default" : "outline"}
                  className={cn(
                    "h-auto py-3",
                    state.tradingMode === mode && "glow-primary"
                  )}
                  onClick={() => onChange({ tradingMode: mode })}
                >
                  <p className="font-medium">{t(`agent.modes.${mode}`)}</p>
                </Button>
              ))}
            </div>
          </div>

          {/* Trading Instructions */}
          <div className="space-y-2">
            <Label>{t("agent.instructions")}</Label>
            <Textarea
              placeholder={t("agent.instructionsPlaceholder")}
              value={state.prompt}
              onChange={(e) => onChange({ prompt: e.target.value })}
              className="bg-muted/50 min-h-[120px]"
            />
            <p className="text-xs text-muted-foreground">
              {t("agent.instructionsHint")}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={onBack} className="flex-1">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t("common.back")}
            </Button>
            <Button
              onClick={onNext}
              disabled={!canProceed}
              className="flex-1 glow-primary"
            >
              <ArrowRight className="w-4 h-4 mr-2" />
              {t("common.next")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Step 4: Risk Config
function RiskStep({
  t,
  state,
  onChange,
  onNext,
  onBack,
}: {
  t: ReturnType<typeof useTranslations>;
  state: OnboardingState;
  onChange: (updates: Partial<OnboardingState>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="mx-auto p-4 rounded-full bg-primary/10 mb-3 w-fit">
          <Shield className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">{t("risk.title")}</h2>
        <p className="text-muted-foreground">{t("risk.description")}</p>
      </div>

      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="p-6 space-y-6">
          {/* Max Leverage */}
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>{t("risk.maxLeverage")}</Label>
              <span className="text-sm font-mono font-semibold">
                {state.maxLeverage}x
              </span>
            </div>
            <Slider
              value={[state.maxLeverage]}
              onValueChange={([value]) => onChange({ maxLeverage: value })}
              min={1}
              max={20}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1x</span>
              <span>20x</span>
            </div>
          </div>

          {/* Max Position Size */}
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>{t("risk.maxPositionSize")}</Label>
              <span className="text-sm font-mono font-semibold">
                {state.maxPositionSize}%
              </span>
            </div>
            <Slider
              value={[state.maxPositionSize]}
              onValueChange={([value]) => onChange({ maxPositionSize: value })}
              min={1}
              max={50}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1%</span>
              <span>50%</span>
            </div>
          </div>

          {/* Max Exposure */}
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>{t("risk.maxExposure")}</Label>
              <span className="text-sm font-mono font-semibold">
                {state.maxExposure}%
              </span>
            </div>
            <Slider
              value={[state.maxExposure]}
              onValueChange={([value]) => onChange({ maxExposure: value })}
              min={10}
              max={100}
              step={5}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Confidence Threshold */}
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>{t("risk.confidenceThreshold")}</Label>
              <span className="text-sm font-mono font-semibold">
                {state.confidenceThreshold}%
              </span>
            </div>
            <Slider
              value={[state.confidenceThreshold]}
              onValueChange={([value]) => onChange({ confidenceThreshold: value })}
              min={50}
              max={95}
              step={5}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>50%</span>
              <span>95%</span>
            </div>
          </div>

          {/* Recommendation */}
          <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <p className="text-sm text-yellow-600 dark:text-yellow-400">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              {t("risk.recommendation")}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={onBack} className="flex-1">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t("common.back")}
            </Button>
            <Button onClick={onNext} className="flex-1 glow-primary">
              <ArrowRight className="w-4 h-4 mr-2" />
              {t("common.next")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Step 5: Launch
function LaunchStep({
  t,
  state,
  onBack,
  onLaunch,
  onSkip,
  isLoading,
}: {
  t: ReturnType<typeof useTranslations>;
  state: OnboardingState;
  onBack: () => void;
  onLaunch: () => void;
  onSkip: () => void;
  isLoading: boolean;
}) {
  const [confirmed, setConfirmed] = useState(false);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="mx-auto p-4 rounded-full bg-primary/10 mb-3 w-fit">
          <Rocket className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">{t("launch.title")}</h2>
        <p className="text-muted-foreground">{t("launch.description")}</p>
      </div>

      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="p-6 space-y-5">
          {/* Configuration Preview */}
          <div className="p-5 rounded-lg bg-muted/30 space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("launch.agentName")}</span>
              <span className="font-medium">{state.agentName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("launch.exchange")}</span>
              <span className="font-medium">
                {EXCHANGES.find((e) => e.id === state.exchange)?.name}
                {state.isTestnet && (
                  <Badge variant="outline" className="ml-2 text-xs">
                    Testnet
                  </Badge>
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("launch.pairs")}</span>
              <span className="font-medium">{state.tradingPairs.join(", ")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("launch.mode")}</span>
              <span className="font-medium capitalize">{state.tradingMode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("launch.maxLeverage")}
              </span>
              <span className="font-mono">{state.maxLeverage}x</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("launch.maxPosition")}
              </span>
              <span className="font-mono">{state.maxPositionSize}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t("launch.confidence")}
              </span>
              <span className="font-mono">{state.confidenceThreshold}%</span>
            </div>
          </div>

          {/* Confirmation */}
          {state.isTestnet && (
            <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/30">
              <input
                type="checkbox"
                id="confirm"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="w-4 h-4"
              />
              <label htmlFor="confirm" className="text-sm">
                {t("launch.confirmTestnet")}
              </label>
            </div>
          )}

          {/* Launch Button */}
          <Button
            size="lg"
            className="w-full glow-primary"
            onClick={onLaunch}
            disabled={isLoading || (state.isTestnet && !confirmed)}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                {t("launch.launching")}
              </>
            ) : (
              <>
                <Rocket className="w-4 h-4 mr-2" />
                {t("launch.launchAgent")}
              </>
            )}
          </Button>

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="outline" onClick={onBack} className="flex-1">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t("launch.modifyConfig")}
            </Button>
            <Button variant="ghost" onClick={onSkip} className="flex-1">
              {t("launch.skipForNow")}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Props for the inline wizard
interface InlineOnboardingWizardProps {
  onComplete?: () => void;
}

// Main Inline Onboarding Wizard
export function InlineOnboardingWizard({ onComplete }: InlineOnboardingWizardProps) {
  const t = useTranslations("onboarding");
  const [step, setStep] = useState(0);
  const [state, setState] = useState<OnboardingState>(initialState);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accountId, setAccountId] = useState<string | null>(null);

  const handleChange = (updates: Partial<OnboardingState>) => {
    setState((prev) => ({ ...prev, ...updates }));
    setError(null);
  };

  const handleNext = () => setStep((s) => s + 1);
  const handleBack = () => setStep((s) => s - 1);

  const handleAccountCreate = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { accountsApi } = await import("@/lib/api");
      const selectedExchange = EXCHANGES.find((e) => e.id === state.exchange);

      const account = await accountsApi.create({
        name: state.accountName,
        exchange: state.exchange as "hyperliquid" | "binance" | "bybit" | "okx",
        is_testnet: state.isTestnet,
        ...(selectedExchange?.requiresPrivateKey
          ? state.hlImportType === "mnemonic"
            ? { mnemonic: state.mnemonic }
            : { private_key: state.privateKey }
          : { api_key: state.apiKey, api_secret: state.apiSecret }),
      });

      setAccountId(account.id);
      handleNext();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create account");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLaunch = async () => {
    setIsLoading(true);
    try {
      const { strategiesApi, agentsApi } = await import("@/lib/api");

      const symbols = state.tradingPairs.map((p) => p.replace("/", ""));
      const tradingMode = state.tradingMode === "moderate" ? "conservative" : state.tradingMode;

      // Step 1: Create strategy template
      const strategy = await strategiesApi.create({
        type: "ai",
        name: state.agentName,
        symbols,
        config: {
          prompt: state.prompt,
          trading_mode: tradingMode,
          risk_controls: {
            maxLeverage: state.maxLeverage,
            maxPositionRatio: state.maxPositionSize / 100,
            maxTotalExposure: state.maxExposure / 100,
            minRiskRewardRatio: state.confidenceThreshold,
          },
        },
      });

      // Step 2: Create agent binding
      await agentsApi.create({
        name: state.agentName,
        strategy_id: strategy.id,
        execution_mode: "live",
        account_id: accountId!,
      });

      // Reset state and call onComplete
      setState(initialState);
      setStep(0);
      setAccountId(null);
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = () => {
    setState(initialState);
    setStep(0);
    setAccountId(null);
    onComplete?.();
  };

  return (
    <div className="space-y-6">
      <StepIndicator currentStep={step} />

      {step === 0 && <WelcomeStep t={t} onNext={handleNext} />}
      {step === 1 && (
        <AccountStep
          t={t}
          state={state}
          onChange={handleChange}
          onNext={handleAccountCreate}
          onBack={handleBack}
          isLoading={isLoading}
          error={error}
        />
      )}
      {step === 2 && (
        <AgentStep
          t={t}
          state={state}
          onChange={handleChange}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}
      {step === 3 && (
        <RiskStep
          t={t}
          state={state}
          onChange={handleChange}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}
      {step === 4 && (
        <LaunchStep
          t={t}
          state={state}
          onBack={handleBack}
          onLaunch={handleLaunch}
          onSkip={handleSkip}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
