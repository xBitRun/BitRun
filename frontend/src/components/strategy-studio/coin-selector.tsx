"use client";

import { useMemo, useState } from "react";
import { X, Plus, Search, TrendingUp, DollarSign, Gem, Info } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { POPULAR_SYMBOLS, FOREX_SYMBOLS, METALS_SYMBOLS, detectMarketType } from "@/types";
import type { MarketType } from "@/types";
import { useTranslations } from "next-intl";

interface CoinSelectorProps {
  value: string[];
  onChange: (symbols: string[]) => void;
  maxCoins?: number;
}

export function CoinSelector({
  value,
  onChange,
  maxCoins = 10,
}: CoinSelectorProps) {
  const t = useTranslations("strategyStudio");
  const [searchQuery, setSearchQuery] = useState("");
  const [customInput, setCustomInput] = useState("");

  const handleAddSymbol = (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim();
    if (
      upperSymbol &&
      !value.includes(upperSymbol) &&
      value.length < maxCoins
    ) {
      onChange([...value, upperSymbol]);
    }
  };

  const handleRemoveSymbol = (symbol: string) => {
    onChange(value.filter((s) => s !== symbol));
  };

  const handleAddCustom = () => {
    if (customInput.trim()) {
      handleAddSymbol(customInput);
      setCustomInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddCustom();
    }
  };

  const filteredPopularSymbols = POPULAR_SYMBOLS.filter(
    (symbol) =>
      !value.includes(symbol) &&
      symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredForexSymbols = FOREX_SYMBOLS.filter(
    (symbol) =>
      !value.includes(symbol) &&
      symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredMetalsSymbols = METALS_SYMBOLS.filter(
    (symbol) =>
      !value.includes(symbol) &&
      symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  /** Badge color hint based on market type */
  const getBadgeClass = (symbol: string) => {
    const mt = detectMarketType(symbol);
    if (mt === "forex") return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    if (mt === "metals") return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    return "";
  };

  /** Get tooltip label for market type */
  const getMarketLabel = (mt: MarketType) => {
    if (mt === "forex") return t("coinSelector.marketType.forex");
    if (mt === "metals") return t("coinSelector.marketType.metals");
    return t("coinSelector.marketType.crypto");
  };

  /** Detect if selection contains mixed market types */
  const selectedMarketTypes = useMemo(() => {
    const types = new Set(value.map((s) => detectMarketType(s)));
    return types;
  }, [value]);

  const hasNonCrypto = selectedMarketTypes.has("forex") || selectedMarketTypes.has("metals");

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <TrendingUp className="h-5 w-5 text-primary" />
          {t("coinSelector.title")}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("coinSelector.description")}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Selected Instruments */}
        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t("coinSelector.selectedCoins")} ({value.length}/{maxCoins})
          </label>
          <div className="flex flex-wrap gap-2 min-h-[40px] p-3 rounded-md border border-border/50 bg-background/50">
            {value.length === 0 ? (
              <span className="text-sm text-muted-foreground">
                {t("coinSelector.noCoinsSelected")}
              </span>
            ) : (
              <TooltipProvider delayDuration={200}>
                {value.map((symbol) => {
                  const mt = detectMarketType(symbol);
                  return (
                    <Tooltip key={symbol}>
                      <TooltipTrigger asChild>
                        <Badge
                          variant="secondary"
                          className={`px-3 py-1 text-sm font-medium gap-1 cursor-default ${getBadgeClass(symbol)}`}
                        >
                          {symbol}
                          <button
                            onClick={() => handleRemoveSymbol(symbol)}
                            className="ml-1 hover:text-destructive transition-colors"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="text-xs">
                        {getMarketLabel(mt)}
                      </TooltipContent>
                    </Tooltip>
                  );
                })}
              </TooltipProvider>
            )}
          </div>

          {/* Mixed market warning */}
          {hasNonCrypto && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400">
              <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{t("coinSelector.mixedMarketWarning")}</span>
            </div>
          )}
        </div>

        {/* Market Type Tabs */}
        <Tabs defaultValue="crypto" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="crypto" className="text-xs sm:text-sm">
              <TrendingUp className="h-3.5 w-3.5 mr-1" />
              {t("coinSelector.marketType.crypto")}
            </TabsTrigger>
            <TabsTrigger value="forex" className="text-xs sm:text-sm">
              <DollarSign className="h-3.5 w-3.5 mr-1" />
              {t("coinSelector.marketType.forex")}
            </TabsTrigger>
            <TabsTrigger value="metals" className="text-xs sm:text-sm">
              <Gem className="h-3.5 w-3.5 mr-1" />
              {t("coinSelector.marketType.metals")}
            </TabsTrigger>
          </TabsList>

          {/* Search (shared) */}
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t("coinSelector.searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Crypto Tab */}
          <TabsContent value="crypto" className="mt-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("coinSelector.popularCoins")}
              </label>
              <div className="flex flex-wrap gap-2">
                {filteredPopularSymbols.map((symbol) => (
                  <Button
                    key={symbol}
                    variant="outline"
                    size="sm"
                    onClick={() => handleAddSymbol(symbol)}
                    disabled={value.length >= maxCoins}
                    className="text-xs"
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    {symbol}
                  </Button>
                ))}
                {filteredPopularSymbols.length === 0 && (
                  <span className="text-sm text-muted-foreground">
                    {t("coinSelector.noResults")}
                  </span>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Forex Tab */}
          <TabsContent value="forex" className="mt-3">
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t("coinSelector.forexSymbols")}
                </label>
                <div className="flex flex-wrap gap-2">
                  {filteredForexSymbols.map((symbol) => (
                    <Button
                      key={symbol}
                      variant="outline"
                      size="sm"
                      onClick={() => handleAddSymbol(symbol)}
                      disabled={value.length >= maxCoins}
                      className="text-xs border-blue-500/20 hover:border-blue-500/40"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {symbol}
                    </Button>
                  ))}
                  {filteredForexSymbols.length === 0 && (
                    <span className="text-sm text-muted-foreground">
                      {t("coinSelector.noResults")}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("coinSelector.forexNote")}
              </p>
            </div>
          </TabsContent>

          {/* Metals Tab */}
          <TabsContent value="metals" className="mt-3">
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t("coinSelector.metalsSymbols")}
                </label>
                <div className="flex flex-wrap gap-2">
                  {filteredMetalsSymbols.map((symbol) => (
                    <Button
                      key={symbol}
                      variant="outline"
                      size="sm"
                      onClick={() => handleAddSymbol(symbol)}
                      disabled={value.length >= maxCoins}
                      className="text-xs border-amber-500/20 hover:border-amber-500/40"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {symbol}
                    </Button>
                  ))}
                  {filteredMetalsSymbols.length === 0 && (
                    <span className="text-sm text-muted-foreground">
                      {t("coinSelector.noResults")}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("coinSelector.metalsNote")}
              </p>
            </div>
          </TabsContent>
        </Tabs>

        {/* Custom Symbol Input */}
        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t("coinSelector.addCustom")}
          </label>
          <div className="flex gap-2">
            <Input
              placeholder={t("coinSelector.customPlaceholder")}
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              className="flex-1"
              maxLength={10}
            />
            <Button
              variant="secondary"
              onClick={handleAddCustom}
              disabled={!customInput.trim() || value.length >= maxCoins}
            >
              <Plus className="h-4 w-4 mr-1" />
              {t("coinSelector.add")}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
