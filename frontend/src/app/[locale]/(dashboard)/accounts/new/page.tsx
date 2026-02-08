"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  Wallet,
  Lightbulb,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { FormPageHeader, CollapsibleCard } from "@/components/layout";
import { useCreateAccount } from "@/hooks";
import type { CreateAccountRequest } from "@/lib/api";
import { accountsApi } from "@/lib/api";
import type { ExchangeType } from "@/types";

const exchangeOptions = [
  { value: "hyperliquid", label: "Hyperliquid (DEX)", icon: "🔷", description: "Decentralized perpetual exchange" },
  { value: "binance", label: "Binance", icon: "🟡", description: "World's largest crypto exchange" },
  { value: "bybit", label: "Bybit", icon: "🟠", description: "Popular derivatives exchange" },
  { value: "okx", label: "OKX", icon: "⬛", description: "Global crypto exchange" },
];

export default function NewAccountPage() {
  const t = useTranslations("accounts");
  const tNew = useTranslations("accounts.newPage");
  const router = useRouter();
  const toast = useToast();
  const { trigger: createAccount } = useCreateAccount();

  const [showSecret, setShowSecret] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showTips, setShowTips] = useState(false);
  const [showSecurity, setShowSecurity] = useState(false);
  const [newAccount, setNewAccount] = useState({
    name: "",
    exchange: "hyperliquid" as ExchangeType,
    isTestnet: false,
    apiKey: "",
    apiSecret: "",
    mnemonic: "",
  });
  const [hlImportType, setHlImportType] = useState<"privateKey" | "mnemonic">("privateKey");

  const [submitPhase, setSubmitPhase] = useState<"idle" | "creating" | "testing">("idle");

  const handleCreateAccount = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitPhase("creating");

    try {
      const request: CreateAccountRequest = {
        name: newAccount.name,
        exchange: newAccount.exchange,
        is_testnet: newAccount.isTestnet,
        ...(newAccount.exchange === "hyperliquid"
          ? hlImportType === "mnemonic"
            ? { mnemonic: newAccount.mnemonic }
            : { private_key: newAccount.apiKey }
          : { api_key: newAccount.apiKey, api_secret: newAccount.apiSecret }),
      };

      const account = await createAccount(request);

      // Auto test connection
      setSubmitPhase("testing");
      try {
        await accountsApi.testConnection(account.id);
        toast.success(tNew("success"), tNew("connectionOk"));
      } catch {
        toast.warning(tNew("success"), tNew("connectionFailed"));
      }

      router.push("/accounts");
    } catch (err) {
      const message = err instanceof Error ? err.message : tNew("createError");
      setSubmitError(message);
      toast.error(tNew("failed"), message);
    } finally {
      setIsSubmitting(false);
      setSubmitPhase("idle");
    }
  };

  const isFormValid = Boolean(
    newAccount.name &&
    (newAccount.exchange === "hyperliquid"
      ? hlImportType === "mnemonic"
        ? newAccount.mnemonic
        : newAccount.apiKey
      : newAccount.apiKey && newAccount.apiSecret)
  );

  const selectedExchange = exchangeOptions.find((e) => e.value === newAccount.exchange);

  const submitLabel = submitPhase === "testing"
    ? tNew("testingConnection")
    : submitPhase === "creating"
      ? tNew("creating")
      : t("dialog.addAccount");

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header - Using shared FormPageHeader component */}
      <FormPageHeader
        backHref="/accounts"
        title={t("dialog.title")}
        subtitle={t("dialog.description")}
        icon={<Wallet className="w-6 h-6 text-primary" />}
        cancelLabel={t("dialog.cancel")}
        submitLabel={submitLabel}
        onSubmit={handleCreateAccount}
        isSubmitting={isSubmitting}
        isValid={isFormValid}
      />

      {/* Error Alert */}
      {submitError && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{submitError}</p>
        </div>
      )}

      {/* Basic Info - Compact Row */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Account Name */}
            <div className="space-y-2">
              <Label htmlFor="name" className="flex items-center gap-2">
                <Wallet className="w-4 h-4 text-primary" />
                {t("dialog.accountName")}
              </Label>
              <Input
                id="name"
                placeholder={t("dialog.accountNamePlaceholder")}
                value={newAccount.name}
                onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
              />
            </div>

            {/* Exchange Selection */}
            <div className="space-y-2">
              <Label htmlFor="exchange">{t("dialog.exchange")}</Label>
              <Select
                value={newAccount.exchange}
                onValueChange={(v) =>
                  setNewAccount({ ...newAccount, exchange: v as ExchangeType })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {exchangeOptions.map((exchange) => (
                    <SelectItem key={exchange.value} value={exchange.value}>
                      <div className="flex items-center gap-2">
                        <span>{exchange.icon}</span>
                        <span>{exchange.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Testnet Toggle */}
            <div className="space-y-2">
              <Label>{t("dialog.testnetMode")}</Label>
              <div className="flex items-center justify-between h-10 px-3 rounded-md border border-input bg-background">
                <span className="text-sm text-muted-foreground">
                  {newAccount.isTestnet ? tNew("testnet") : tNew("mainnet")}
                </span>
                <Switch
                  checked={newAccount.isTestnet}
                  onCheckedChange={(v) => setNewAccount({ ...newAccount, isTestnet: v })}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Credentials Card - Core Section */}
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-primary" />
                {tNew("credentials")}
              </CardTitle>
              <CardDescription className="mt-1">
                {tNew("credentialsDesc")}
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowTips(!showTips)}
              className="text-muted-foreground"
            >
              <Lightbulb className="w-4 h-4 mr-1" />
              {tNew("tips")}
              {showTips ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
            </Button>
          </div>

          {/* Collapsible Tips */}
          {showTips && (
            <div className="mt-4 p-4 rounded-lg bg-muted/50 text-sm space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="font-medium mb-1">{tNew("tipTestnet")}</p>
                  <p className="text-muted-foreground text-xs">
                    {tNew("tipTestnetDesc")}
                  </p>
                </div>
                <div>
                  <p className="font-medium mb-1">{tNew("tipSubaccount")}</p>
                  <p className="text-muted-foreground text-xs">
                    {tNew("tipSubaccountDesc")}
                  </p>
                </div>
                <div>
                  <p className="font-medium mb-1">{tNew("tipWhitelist")}</p>
                  <p className="text-muted-foreground text-xs">
                    {tNew("tipWhitelistDesc")}
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Exchange Info Banner */}
          {selectedExchange && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
              <span className="text-2xl">{selectedExchange.icon}</span>
              <div>
                <p className="font-medium">{selectedExchange.label}</p>
                <p className="text-xs text-muted-foreground">
                    {newAccount.exchange === "hyperliquid"
                    ? tNew("hyperliquidInfo")
                    : tNew("cexInfo")}
                </p>
              </div>
            </div>
          )}

          {/* Hyperliquid: Import Type Selection */}
          {newAccount.exchange === "hyperliquid" && (
            <div className="space-y-3">
              <Label>{t("dialog.importType")}</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setHlImportType("privateKey")}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    hlImportType === "privateKey"
                      ? "border-primary/50 bg-primary/10"
                      : "border-border/50 hover:border-border"
                  }`}
                >
                  <p className="font-medium text-sm">{t("dialog.privateKey")}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {tNew("privateKeyDesc")}
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => setHlImportType("mnemonic")}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    hlImportType === "mnemonic"
                      ? "border-primary/50 bg-primary/10"
                      : "border-border/50 hover:border-border"
                  }`}
                >
                  <p className="font-medium text-sm">{t("dialog.mnemonic")}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {tNew("mnemonicDesc")}
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Credential Input Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Hyperliquid: Private Key */}
            {newAccount.exchange === "hyperliquid" && hlImportType === "privateKey" && (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="apiKey">{t("dialog.privateKey")}</Label>
                <div className="relative">
                  <Input
                    id="apiKey"
                    type={showSecret ? "text" : "password"}
                    placeholder="0x..."
                    value={newAccount.apiKey}
                    onChange={(e) => setNewAccount({ ...newAccount, apiKey: e.target.value })}
                    className="pr-10 font-mono"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full"
                    onClick={() => setShowSecret(!showSecret)}
                  >
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
            )}

            {/* Hyperliquid: Mnemonic */}
            {newAccount.exchange === "hyperliquid" && hlImportType === "mnemonic" && (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="mnemonic">{t("dialog.mnemonic")}</Label>
                <div className="relative">
                  <Input
                    id="mnemonic"
                    type={showSecret ? "text" : "password"}
                    placeholder={t("dialog.mnemonicPlaceholder")}
                    value={newAccount.mnemonic}
                    onChange={(e) => setNewAccount({ ...newAccount, mnemonic: e.target.value })}
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full"
                    onClick={() => setShowSecret(!showSecret)}
                  >
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">{t("dialog.mnemonicHint")}</p>
              </div>
            )}

            {/* CEX: API Key & Secret */}
            {newAccount.exchange !== "hyperliquid" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="apiKey">{t("dialog.apiKey")}</Label>
                  <Input
                    id="apiKey"
                    type="text"
                    placeholder={t("dialog.enterApiKey")}
                    value={newAccount.apiKey}
                    onChange={(e) => setNewAccount({ ...newAccount, apiKey: e.target.value })}
                    className="font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="apiSecret">{t("dialog.apiSecret")}</Label>
                  <div className="relative">
                    <Input
                      id="apiSecret"
                      type={showSecret ? "text" : "password"}
                      placeholder={t("dialog.enterApiSecret")}
                      value={newAccount.apiSecret}
                      onChange={(e) =>
                        setNewAccount({ ...newAccount, apiSecret: e.target.value })
                      }
                      className="pr-10 font-mono"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full"
                      onClick={() => setShowSecret(!showSecret)}
                    >
                      {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Security Notice - Collapsible */}
      <CollapsibleCard
        open={showSecurity}
        onOpenChange={setShowSecurity}
        title={tNew("securityTitle")}
        description={tNew("securitySubtitle")}
        icon={<ShieldCheck className="w-4 h-4 text-primary" />}
      >
        <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
          <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-primary">
              {tNew("encryptionTitle")}
            </p>
            <p className="text-sm text-muted-foreground">{t("dialog.encryptionNote")}</p>
          </div>
        </div>
      </CollapsibleCard>
    </div>
  );
}
