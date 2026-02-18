"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { FlaskConical, Play, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { SymbolSelector } from "@/components/symbol-selector";
import {
  useStrategies,
  useCreateBacktest,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
} from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { BacktestExchange } from "@/lib/api";

// Supported exchanges for backtesting
const EXCHANGE_OPTIONS: {
  value: BacktestExchange;
  label: string;
  icon: string;
}[] = [
  { value: "binance", label: "Binance", icon: "🟡" },
  { value: "bybit", label: "Bybit", icon: "🟠" },
  { value: "okx", label: "OKX", icon: "⬛" },
  { value: "hyperliquid", label: "Hyperliquid", icon: "🔷" },
];

export default function RunBacktestPage() {
  const t = useTranslations("backtest");
  const router = useRouter();
  const toast = useToast();
  const { data: strategies } = useStrategies();
  const { trigger: createBacktest, isMutating: isRunning } =
    useCreateBacktest();
  const { models } = useUserModels();

  // Exchange state
  const [selectedExchange, setSelectedExchange] =
    useState<BacktestExchange>("hyperliquid");

  // Form state
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [startDate, setStartDate] = useState<Date | undefined>();
  const [endDate, setEndDate] = useState<Date | undefined>();
  const [initialBalance, setInitialBalance] = useState<string>("10000");

  // Determine if selected strategy is AI-based
  const selectedStrategyData = (strategies || []).find(
    (s) => s.id === selectedStrategy,
  );
  const isAiStrategy = selectedStrategyData?.type === "ai";

  const handleExchangeChange = (value: string) => {
    setSelectedExchange(value as BacktestExchange);
    setSelectedSymbols([]);
  };

  const handleRunBacktest = async () => {
    if (
      !selectedStrategy ||
      selectedSymbols.length === 0 ||
      !startDate ||
      !endDate
    )
      return;

    try {
      const result = await createBacktest({
        strategy_id: selectedStrategy,
        start_date: format(startDate, "yyyy-MM-dd"),
        end_date: format(endDate, "yyyy-MM-dd"),
        initial_balance: parseFloat(initialBalance),
        symbols: selectedSymbols,
        exchange: selectedExchange,
        // Pass AI model for AI strategies
        ai_model: isAiStrategy ? selectedModel || undefined : undefined,
      });

      if (result) {
        toast.success(
          t("toast.completed"),
          `Total return: ${result.total_return_percent?.toFixed(2)}%`,
        );
        // Navigate to the detail page
        router.push(`/backtest/${result.id}`);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : t("toast.failed");
      toast.error(t("toast.failed"), message);
    }
  };

  const canRun =
    selectedStrategy &&
    selectedSymbols.length > 0 &&
    startDate &&
    endDate &&
    !isRunning &&
    // AI strategies must have a selected model
    (!isAiStrategy || selectedModel);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gradient">{t("run.title")}</h1>
        <p className="text-muted-foreground">{t("run.subtitle")}</p>
      </div>

      {/* Configuration Panel */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-primary" />
            {t("configuration")}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 items-end">
          {/* Exchange Selection */}
          <div className="space-y-2">
            <Label>{t("dataSource")}</Label>
            <Select
              value={selectedExchange}
              onValueChange={handleExchangeChange}
            >
              <SelectTrigger className="bg-muted/50">
                <SelectValue placeholder={t("selectExchange")} />
              </SelectTrigger>
              <SelectContent>
                {EXCHANGE_OPTIONS.map((ex) => (
                  <SelectItem key={ex.value} value={ex.value}>
                    <span className="flex items-center gap-2">
                      <span>{ex.icon}</span>
                      <span>{ex.label}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Strategy Selection */}
          <div className="space-y-2">
            <Label>{t("run.selectStrategy")}</Label>
            <Select
              value={selectedStrategy}
              onValueChange={setSelectedStrategy}
            >
              <SelectTrigger className="bg-muted/50">
                <SelectValue placeholder={t("run.selectStrategyPlaceholder")} />
              </SelectTrigger>
              <SelectContent>
                {(strategies || []).map((strategy) => (
                  <SelectItem key={strategy.id} value={strategy.id}>
                    {strategy.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* AI Model Selection - Only shown for AI strategies */}
          {isAiStrategy && (
            <div className="space-y-2">
              <Label>{t("aiModel")}</Label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="bg-muted/50">
                  <SelectValue placeholder={t("selectModel")} />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(groupModelsByProvider(models || [])).map(
                    ([provider, providerModels]) => (
                      <SelectGroup key={provider}>
                        <SelectLabel>
                          {getProviderDisplayName(provider)}
                        </SelectLabel>
                        {providerModels.map((model) => (
                          <SelectItem key={model.id} value={model.id}>
                            {model.name}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Trading Pairs (Multi-select) */}
          <div className="space-y-2 lg:col-span-2">
            <Label>{t("tradingPair")}</Label>
            <SymbolSelector
              value={selectedSymbols}
              onChange={(value) => setSelectedSymbols(value as string[])}
              mode="multiple"
              exchange={selectedExchange}
              placeholder={t("selectPair")}
              className="bg-muted/50"
              showMarketTypeTabs={false}
            />
          </div>

          {/* Time Range */}
          <div className="space-y-2 lg:col-span-2">
            <Label>{t("timeRange")}</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-muted-foreground">
                  {t("startDate")}
                </Label>
                <DatePicker
                  value={startDate}
                  onChange={setStartDate}
                  placeholder={t("startDate")}
                  toDate={endDate}
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">
                  {t("endDate")}
                </Label>
                <DatePicker
                  value={endDate}
                  onChange={setEndDate}
                  placeholder={t("endDate")}
                  fromDate={startDate}
                  toDate={new Date()}
                />
              </div>
            </div>
          </div>

          {/* Initial Balance */}
          <div className="space-y-2">
            <Label>{t("initialBalance")}</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                type="number"
                value={initialBalance}
                onChange={(e) => setInitialBalance(e.target.value)}
                className="pl-7 bg-muted/50"
                min={100}
              />
            </div>
          </div>

          {/* Run Button */}
          <Button
            onClick={handleRunBacktest}
            disabled={!canRun}
            className="gap-2"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t("running")}
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                {t("run.runButton")}
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
