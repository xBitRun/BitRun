"use client";

import { use, useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, Save, X, Plus, Globe, Lock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useStrategy, useUpdateStrategy } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { StrategyVisibility } from "@/types";

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

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<StrategyVisibility>("private");
  const [symbolInput, setSymbolInput] = useState("");
  const [symbols, setSymbols] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);

  // Initialize form from strategy data
  useEffect(() => {
    if (strategy) {
      setName(strategy.name);
      setDescription(strategy.description || "");
      setVisibility(strategy.visibility);
      setSymbols(strategy.symbols);
      setTags(strategy.tags);
    }
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
      });
      toast.success(t("toast.updated"));
      router.push(`/strategies/${id}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.updateFailed");
      toast.error(t("error.updateFailed"), message);
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

      {/* Basic Info */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>{t("create.basicInfo")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("create.name")}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("create.namePlaceholder")}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("create.descriptionLabel")}
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("create.descriptionPlaceholder")}
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* Trading Symbols */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>{t("create.symbol")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
            />
            <Button variant="outline" onClick={handleAddSymbol}>
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {symbols.map((symbol) => (
              <Badge
                key={symbol}
                variant="secondary"
                className="font-mono pr-1"
              >
                {symbol}
                <button
                  onClick={() => handleRemoveSymbol(symbol)}
                  className="ml-1.5 hover:text-destructive transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Visibility */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>{t("detail.settings.visibility")}</CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>

      {/* Tags */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle>{t("edit.tags")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
          <div className="flex flex-wrap gap-2">
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
