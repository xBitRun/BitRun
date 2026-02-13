"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import {
  ArrowLeft,
  Grid3X3,
  ArrowDownUp,
  Activity,
  Bot,
  Check,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import type { StrategyType } from "@/types";

const STRATEGY_TYPES: {
  type: StrategyType;
  icon: typeof Grid3X3;
  color: string;
}[] = [
  { type: "ai", icon: Bot, color: "text-purple-500 bg-purple-500/10 border-purple-500/30" },
  { type: "grid", icon: Grid3X3, color: "text-blue-500 bg-blue-500/10 border-blue-500/30" },
  { type: "dca", icon: ArrowDownUp, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30" },
  { type: "rsi", icon: Activity, color: "text-violet-500 bg-violet-500/10 border-violet-500/30" },
];

export default function CreateStrategyPage() {
  const t = useTranslations("quantStrategies");
  const router = useRouter();
  const toast = useToast();

  const [step, setStep] = useState(0); // 0: type, 1: basic info, 2: params
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [selectedType, setSelectedType] = useState<StrategyType | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [symbol, setSymbol] = useState("BTC");

  // AI-specific state
  const [aiSymbols, setAiSymbols] = useState("BTC, ETH");
  const [aiTradingMode, setAiTradingMode] = useState<string>("balanced");
  const [aiPrompt, setAiPrompt] = useState("");

  // Grid params
  const [gridUpperPrice, setGridUpperPrice] = useState("50000");
  const [gridLowerPrice, setGridLowerPrice] = useState("40000");
  const [gridCount, setGridCount] = useState("10");
  const [gridTotalInvestment, setGridTotalInvestment] = useState("1000");
  const [gridLeverage, setGridLeverage] = useState("1");

  // DCA params
  const [dcaOrderAmount, setDcaOrderAmount] = useState("100");
  const [dcaIntervalMinutes, setDcaIntervalMinutes] = useState("60");
  const [dcaTakeProfitPercent, setDcaTakeProfitPercent] = useState("5");
  const [dcaTotalBudget, setDcaTotalBudget] = useState("0");
  const [dcaMaxOrders, setDcaMaxOrders] = useState("0");

  // RSI params
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [rsiOverbought, setRsiOverbought] = useState("70");
  const [rsiOversold, setRsiOversold] = useState("30");
  const [rsiOrderAmount, setRsiOrderAmount] = useState("100");
  const [rsiTimeframe, setRsiTimeframe] = useState("1h");
  const [rsiLeverage, setRsiLeverage] = useState("1");

  const isAiType = selectedType === "ai";

  const buildConfig = (): Record<string, unknown> => {
    switch (selectedType) {
      case "ai":
        return {
          trading_mode: aiTradingMode,
          custom_prompt: aiPrompt || undefined,
        };
      case "grid":
        return {
          upper_price: parseFloat(gridUpperPrice),
          lower_price: parseFloat(gridLowerPrice),
          grid_count: parseInt(gridCount),
          total_investment: parseFloat(gridTotalInvestment),
          leverage: parseFloat(gridLeverage),
        };
      case "dca":
        return {
          order_amount: parseFloat(dcaOrderAmount),
          interval_minutes: parseInt(dcaIntervalMinutes),
          take_profit_percent: parseFloat(dcaTakeProfitPercent),
          total_budget: parseFloat(dcaTotalBudget),
          max_orders: parseInt(dcaMaxOrders),
        };
      case "rsi":
        return {
          rsi_period: parseInt(rsiPeriod),
          overbought_threshold: parseFloat(rsiOverbought),
          oversold_threshold: parseFloat(rsiOversold),
          order_amount: parseFloat(rsiOrderAmount),
          timeframe: rsiTimeframe,
          leverage: parseFloat(rsiLeverage),
        };
      default:
        return {};
    }
  };

  const getSymbols = (): string[] => {
    if (isAiType) {
      return aiSymbols
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
    }
    return [symbol.toUpperCase()];
  };

  const handleSubmit = async () => {
    if (!selectedType || !name) return;
    const symbols = getSymbols();
    if (symbols.length === 0) return;

    setIsSubmitting(true);
    try {
      const { strategiesApi } = await import("@/lib/api");
      const strategy = await strategiesApi.create({
        type: selectedType,
        name,
        description,
        symbols,
        config: buildConfig(),
      });
      toast.success(t("toast.createSuccess"));
      // Redirect to the agent wizard with this strategy pre-selected
      router.push(`/agents/new?strategyId=${strategy.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.createFailed");
      toast.error(t("toast.createFailed"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canProceedStep1 = () => {
    if (!name) return false;
    if (isAiType) {
      const symbols = getSymbols();
      return symbols.length > 0;
    }
    return !!symbol;
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/strategies")}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("create.title")}</h1>
          <p className="text-muted-foreground">{t("create.description")}</p>
        </div>
      </div>

      {/* Step 0: Select Strategy Type */}
      {step === 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">{t("create.selectType")}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGY_TYPES.map(({ type, icon: Icon, color }) => (
              <Card
                key={type}
                className={cn(
                  "cursor-pointer transition-all hover:scale-[1.02]",
                  selectedType === type
                    ? "border-primary ring-2 ring-primary/20"
                    : "border-border/50 hover:border-primary/30"
                )}
                onClick={() => setSelectedType(type)}
              >
                <CardContent className="flex flex-col items-center py-8 text-center">
                  <div className={cn("p-4 rounded-xl mb-4 border", color)}>
                    <Icon className="w-8 h-8" />
                  </div>
                  <h3 className="font-semibold text-lg mb-2">{t(`types.${type}`)}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t(`typeDescriptions.${type}`)}
                  </p>
                  {selectedType === type && (
                    <div className="mt-4 p-1 rounded-full bg-primary text-primary-foreground">
                      <Check className="w-4 h-4" />
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => setStep(1)}
              disabled={!selectedType}
            >
              {t("create.next")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 1: Basic Info */}
      {step === 1 && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("create.basicInfo")}</CardTitle>
              <CardDescription>{t("create.basicInfoDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>{t("create.name")}</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("create.namePlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("create.descriptionLabel")}</Label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("create.descriptionPlaceholder")}
                />
              </div>

              {isAiType ? (
                <>
                  {/* AI: multi-symbol input */}
                  <div className="space-y-2">
                    <Label>{t("create.symbols")}</Label>
                    <Input
                      value={aiSymbols}
                      onChange={(e) => setAiSymbols(e.target.value)}
                      placeholder={t("create.symbolsPlaceholder")}
                    />
                  </div>
                  {/* AI: trading mode */}
                  <div className="space-y-2">
                    <Label>{t("create.tradingMode")}</Label>
                    <Select value={aiTradingMode} onValueChange={setAiTradingMode}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="conservative">Conservative</SelectItem>
                        <SelectItem value="balanced">Balanced</SelectItem>
                        <SelectItem value="aggressive">Aggressive</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* AI: prompt */}
                  <div className="space-y-2">
                    <Label>{t("create.prompt")}</Label>
                    <Textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder={t("create.promptPlaceholder")}
                      rows={5}
                    />
                  </div>
                </>
              ) : (
                /* Quant: single symbol */
                <div className="space-y-2">
                  <Label>{t("create.symbol")}</Label>
                  <Input
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder={t("create.symbolPlaceholder")}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(0)}>
              {t("create.back")}
            </Button>
            <Button
              onClick={() => {
                if (isAiType) {
                  // AI strategies skip params step, submit directly
                  handleSubmit();
                } else {
                  setStep(2);
                }
              }}
              disabled={!canProceedStep1() || (isAiType && isSubmitting)}
            >
              {isAiType && isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {isAiType ? t("create.submit") : t("create.next")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Strategy Parameters (quant only) */}
      {step === 2 && !isAiType && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>
                {selectedType === "grid" && t("grid.title")}
                {selectedType === "dca" && t("dca.title")}
                {selectedType === "rsi" && t("rsi.title")}
              </CardTitle>
              <CardDescription>{t("create.parametersDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Grid Parameters */}
              {selectedType === "grid" && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{t("grid.upperPrice")}</Label>
                      <Input
                        type="number"
                        value={gridUpperPrice}
                        onChange={(e) => setGridUpperPrice(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.lowerPrice")}</Label>
                      <Input
                        type="number"
                        value={gridLowerPrice}
                        onChange={(e) => setGridLowerPrice(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("grid.gridCount")}</Label>
                      <Input
                        type="number"
                        value={gridCount}
                        onChange={(e) => setGridCount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.totalInvestment")}</Label>
                      <Input
                        type="number"
                        value={gridTotalInvestment}
                        onChange={(e) => setGridTotalInvestment(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.leverage")}</Label>
                      <Input
                        type="number"
                        value={gridLeverage}
                        onChange={(e) => setGridLeverage(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              {/* DCA Parameters */}
              {selectedType === "dca" && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{t("dca.orderAmount")}</Label>
                      <Input
                        type="number"
                        value={dcaOrderAmount}
                        onChange={(e) => setDcaOrderAmount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.intervalMinutes")}</Label>
                      <Input
                        type="number"
                        value={dcaIntervalMinutes}
                        onChange={(e) => setDcaIntervalMinutes(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("dca.takeProfitPercent")}</Label>
                      <Input
                        type="number"
                        value={dcaTakeProfitPercent}
                        onChange={(e) => setDcaTakeProfitPercent(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.totalBudget")}</Label>
                      <Input
                        type="number"
                        value={dcaTotalBudget}
                        onChange={(e) => setDcaTotalBudget(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.maxOrders")}</Label>
                      <Input
                        type="number"
                        value={dcaMaxOrders}
                        onChange={(e) => setDcaMaxOrders(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              {/* RSI Parameters */}
              {selectedType === "rsi" && (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("rsi.rsiPeriod")}</Label>
                      <Input
                        type="number"
                        value={rsiPeriod}
                        onChange={(e) => setRsiPeriod(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.overboughtThreshold")}</Label>
                      <Input
                        type="number"
                        value={rsiOverbought}
                        onChange={(e) => setRsiOverbought(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.oversoldThreshold")}</Label>
                      <Input
                        type="number"
                        value={rsiOversold}
                        onChange={(e) => setRsiOversold(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("rsi.orderAmount")}</Label>
                      <Input
                        type="number"
                        value={rsiOrderAmount}
                        onChange={(e) => setRsiOrderAmount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.timeframe")}</Label>
                      <Select value={rsiTimeframe} onValueChange={setRsiTimeframe}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1m">1m</SelectItem>
                          <SelectItem value="5m">5m</SelectItem>
                          <SelectItem value="15m">15m</SelectItem>
                          <SelectItem value="30m">30m</SelectItem>
                          <SelectItem value="1h">1h</SelectItem>
                          <SelectItem value="4h">4h</SelectItem>
                          <SelectItem value="1d">1d</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.leverage")}</Label>
                      <Input
                        type="number"
                        value={rsiLeverage}
                        onChange={(e) => setRsiLeverage(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>
              {t("create.back")}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="glow-primary"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {t("create.submit")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
