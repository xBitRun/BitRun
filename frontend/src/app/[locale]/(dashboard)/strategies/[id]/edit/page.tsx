"use client";

import { use, useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Save,
  X,
  Plus,
  Globe,
  Lock,
  AlertTriangle,
  DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { useStrategy, useUpdateStrategy, useStrategyAgents } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { StrategyVisibility } from "@/types";
import { ApiError, agentsApi } from "@/lib/api";
import { StrategyEditDecisionDialog } from "@/components/strategies/StrategyEditDecisionDialog";

export default function StrategyEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("strategies");
  const router = useRouter();
  const toast = useToast();

  const { data: strategy, error, isLoading } = useStrategy(id);
  const { trigger: updateStrategy, isMutating: isUpdating } =
    useUpdateStrategy(id);
  const { activeAgents, hasActiveAgents } = useStrategyAgents(id);

  // Decision dialog state
  const [showDecisionDialog, setShowDecisionDialog] = useState(false);
  const [configUnlocked, setConfigUnlocked] = useState(false);
  const [isPausingAgents, setIsPausingAgents] = useState(false);

  // Determine if config should be locked
  const configLocked = hasActiveAgents && !configUnlocked;

  // Show decision dialog when there are active agents and config is still locked
  useEffect(() => {
    if (hasActiveAgents && !configUnlocked && strategy) {
      setShowDecisionDialog(true);
    }
  }, [hasActiveAgents, configUnlocked, strategy]);

  // Form state - Strategy Config
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [symbolInput, setSymbolInput] = useState("");
  const [symbols, setSymbols] = useState<string[]>([]);

  // Form state - Marketplace Info
  const [visibility, setVisibility] = useState<StrategyVisibility>("private");
  const [category, setCategory] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [isPaid, setIsPaid] = useState(false);
  const [priceMonthly, setPriceMonthly] = useState<string>("");
  const [pricingModel, setPricingModel] = useState<"free" | "monthly">("free");

  // Initialize form from strategy data
  useEffect(() => {
    if (strategy) {
      if (name !== strategy.name) setName(strategy.name);
      if (description !== (strategy.description || "")) {
        setDescription(strategy.description || "");
      }
      if (visibility !== strategy.visibility) setVisibility(strategy.visibility);
      if (JSON.stringify(symbols) !== JSON.stringify(strategy.symbols)) {
        setSymbols(strategy.symbols);
      }
      if (JSON.stringify(tags) !== JSON.stringify(strategy.tags || [])) {
        setTags(strategy.tags || []);
      }
      if (category !== (strategy.category || "")) {
        setCategory(strategy.category || "");
      }
      if (isPaid !== (strategy.is_paid || false)) {
        setIsPaid(strategy.is_paid || false);
      }
      if (priceMonthly !== String(strategy.price_monthly || "")) {
        setPriceMonthly(String(strategy.price_monthly || ""));
      }
      if (pricingModel !== (strategy.pricing_model || "free")) {
        setPricingModel(strategy.pricing_model === "monthly" ? "monthly" : "free");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy]);

  const handleAddSymbol = () => {
    const symbol = symbolInput.trim().toUpperCase();
    if (symbol && !symbols.includes(symbol)) {
      setSymbols([...symbols, symbol]);
      setSymbolInput("");
    }
  };

  const handleRemoveSymbol = (symbol: string) => {
    setSymbols(symbols.filter((s) => s !== symbol));
  };

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !tags.includes(tag)) {
      setTags([...tags, tag]);
      setTagInput("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  // Handler for pausing all active agents and then allowing edit
  const handlePauseAndEdit = async () => {
    setIsPausingAgents(true);
    try {
      // Pause all active agents
      for (const agent of activeAgents) {
        await agentsApi.pause(agent.id);
      }
      toast.success(t("edit.agentsPaused", { count: activeAgents.length }));
      setConfigUnlocked(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("edit.pauseAgentsError");
      toast.error(t("edit.pauseAgentsError"), message);
    } finally {
      setIsPausingAgents(false);
    }
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error(t("edit.nameRequired"));
      return;
    }

    try {
      await updateStrategy({
        name: name.trim(),
        description: description.trim() || undefined,
        visibility,
        symbols,
        tags,
        category: category.trim() || undefined,
        is_paid: isPaid,
        price_monthly: isPaid && priceMonthly ? parseFloat(priceMonthly) : null,
        pricing_model: isPaid ? "monthly" : "free",
      });
      toast.success(t("toast.updated"));
      router.push(`/strategies/${id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Conflict - active agents exist
        toast.error(t("edit.error409", { message: err.message }));
      } else {
        const message =
          err instanceof Error ? err.message : t("error.updateFailed");
        toast.error(t("error.updateFailed"), message);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !strategy) {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        <Button variant="ghost" onClick={() => router.push("/strategies")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("detail.backToStrategies")}
        </Button>
        <Card className="bg-card/50">
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">{t("edit.notFound")}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push(`/strategies/${id}`)}
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gradient">
            {t("edit.title")}
          </h1>
          <p className="text-muted-foreground">{t("edit.backToStrategy")}</p>
        </div>
      </div>

      {/* Active Agent Warning */}
      {configLocked && (
        <Alert variant="destructive" className="border-orange-500/50 bg-orange-500/10">
          <AlertTriangle className="h-4 w-4 text-orange-500" />
          <AlertTitle className="text-orange-500">
            {t("edit.configLocked")}
          </AlertTitle>
          <AlertDescription className="text-orange-400/90">
            {activeAgents.length === 1
              ? t("edit.activeAgentWarningSingle", { name: activeAgents[0].name })
              : t("edit.activeAgentWarning", { count: activeAgents.length })}
            <Button
              variant="link"
              className="px-0 ml-2 text-orange-400 hover:text-orange-300"
              onClick={() => router.push("/agents")}
            >
              {t("edit.goToAgents")} →
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Decision Dialog */}
      {strategy && (
        <StrategyEditDecisionDialog
          open={showDecisionDialog}
          onOpenChange={setShowDecisionDialog}
          strategyId={id}
          strategyName={strategy.name}
          activeAgents={activeAgents}
          onPauseAndEdit={handlePauseAndEdit}
        />
      )}

      {/* Strategy Config Section */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{t("edit.strategyConfigSection")}</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {t("edit.strategyConfigDesc")}
              </p>
            </div>
            {configLocked && (
              <Badge variant="outline" className="border-orange-500/50 text-orange-400">
                {t("edit.pauseAgentFirst")}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("create.name")}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("create.namePlaceholder")}
              disabled={configLocked}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("create.descriptionLabel")}
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("create.descriptionPlaceholder")}
              rows={3}
              disabled={configLocked}
            />
          </div>

          {/* Trading Symbols */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("create.symbol")}</label>
            <div className="flex gap-2">
              <Input
                value={symbolInput}
                onChange={(e) => setSymbolInput(e.target.value)}
                placeholder={t("create.symbolPlaceholder")}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddSymbol();
                  }
                }}
                disabled={configLocked}
              />
              <Button
                variant="outline"
                onClick={handleAddSymbol}
                disabled={configLocked}
              >
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {symbols.map((symbol) => (
                <Badge
                  key={symbol}
                  variant="secondary"
                  className={cn(
                    "font-mono pr-1",
                    configLocked && "opacity-50"
                  )}
                >
                  {symbol}
                  {!configLocked && (
                    <button
                      onClick={() => handleRemoveSymbol(symbol)}
                      className="ml-1.5 hover:text-destructive transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Marketplace Section */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>{t("edit.marketplaceSection")}</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            {t("edit.marketplaceDesc")}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Visibility */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("detail.settings.visibility")}
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => setVisibility("private")}
                className={cn(
                  "flex-1 p-4 rounded-lg border-2 transition-all text-left",
                  visibility === "private"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground/50",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Lock className="w-4 h-4" />
                  <span className="font-medium">{t("visibility.private")}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {t("detail.settings.privateHint")}
                </p>
              </button>
              <button
                onClick={() => setVisibility("public")}
                className={cn(
                  "flex-1 p-4 rounded-lg border-2 transition-all text-left",
                  visibility === "public"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-muted-foreground/50",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Globe className="w-4 h-4" />
                  <span className="font-medium">{t("visibility.public")}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {t("detail.settings.publicHint")}
                </p>
              </button>
            </div>
          </div>

          {/* Category & Tags (only show when public) */}
          {visibility === "public" && (
            <>
              {/* Category */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("edit.category")}</label>
                <Input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder={t("edit.categoryPlaceholder")}
                />
              </div>

              {/* Tags */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("edit.tags")}</label>
                <div className="flex gap-2">
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder={t("edit.tagPlaceholder")}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                  />
                  <Button variant="outline" onClick={handleAddTag}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="pr-1">
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-1.5 hover:text-destructive transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                  {tags.length === 0 && (
                    <span className="text-sm text-muted-foreground">
                      {t("edit.noTags")}
                    </span>
                  )}
                </div>
              </div>

              {/* Paid Strategy */}
              <div className="space-y-4 pt-4 border-t border-border/50">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="isPaid" className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4" />
                      {t("edit.isPaid")}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {t("edit.isPaidHint")}
                    </p>
                  </div>
                  <Switch
                    id="isPaid"
                    checked={isPaid}
                    onCheckedChange={setIsPaid}
                  />
                </div>

                {isPaid && (
                  <div className="space-y-2 pl-4 border-l-2 border-primary/50">
                    <label className="text-sm font-medium">
                      {t("pricing.monthlyPrice")}
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                        $
                      </span>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        value={priceMonthly}
                        onChange={(e) => setPriceMonthly(e.target.value)}
                        placeholder="9.99"
                        className="pl-7"
                      />
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Marketplace Hint */}
          {visibility === "private" && (
            <p className="text-sm text-muted-foreground italic">
              {t("edit.marketplaceHint")}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4">
        <Button variant="outline" asChild>
          <Link href={`/strategies/${id}`}>{t("edit.backToStrategy")}</Link>
        </Button>
        <Button onClick={handleSubmit} disabled={isUpdating}>
          {isUpdating ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          {t("edit.saveChanges")}
        </Button>
      </div>
    </div>
  );
}
