"use client";

import { useState } from "react";
import { X, Plus, Search, TrendingUp } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { POPULAR_SYMBOLS } from "@/types";
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
        {/* Selected Coins */}
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
              value.map((symbol) => (
                <Badge
                  key={symbol}
                  variant="secondary"
                  className="px-3 py-1 text-sm font-medium gap-1"
                >
                  {symbol}
                  <button
                    onClick={() => handleRemoveSymbol(symbol)}
                    className="ml-1 hover:text-destructive transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))
            )}
          </div>
        </div>

        {/* Popular Coins */}
        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t("coinSelector.popularCoins")}
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t("coinSelector.searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
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

        {/* Custom Coin Input */}
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
