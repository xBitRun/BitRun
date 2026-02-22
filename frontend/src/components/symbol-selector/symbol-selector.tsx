"use client";

import { useState, useMemo, useCallback } from "react";
import {
  Check,
  ChevronsUpDown,
  X,
  Loader2,
  TrendingUp,
  DollarSign,
  Gem,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { useTranslations } from "next-intl";
import { useSymbolsList } from "@/hooks/use-symbols";
import { useSettlementCurrency } from "@/hooks/use-exchange-capabilities";
import {
  POPULAR_CRYPTO_SYMBOLS,
  FOREX_SYMBOLS,
  METALS_SYMBOLS,
  detectMarketType,
} from "./constants";
import type {
  SymbolSelectorProps,
  SymbolOption,
  SymbolSelectorMode,
} from "./types";

/**
 * Unified Symbol Selector Component
 *
 * A searchable dropdown component for selecting trading pairs.
 * Supports both single and multiple selection modes.
 * Integrates with CCXT API to fetch available symbols from exchanges.
 *
 * When exchange is provided, automatically uses the correct settlement currency:
 * - Hyperliquid: USDC
 * - Other exchanges: USDT
 */
export function SymbolSelector({
  value,
  onChange,
  mode = "multiple",
  maxSelections = 10,
  exchange,
  assetType = "crypto_perp",
  showMarketTypeTabs = true,
  placeholder,
  disabled = false,
  size = "md",
  className,
  allowCustomInput = true,
}: SymbolSelectorProps) {
  const t = useTranslations("symbolSelector");
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"crypto" | "forex" | "metals">(
    "crypto",
  );
  const [customInput, setCustomInput] = useState("");

  // Map MarketType to tab category
  const getTabCategory = (
    marketType: string,
  ): "crypto" | "forex" | "metals" => {
    if (marketType === "forex") return "forex";
    if (marketType === "metals") return "metals";
    return "crypto"; // crypto_perp, crypto_spot -> crypto
  };

  // Get settlement currency for this exchange and asset type
  const { settlement } = useSettlementCurrency(exchange, assetType);

  // Fetch symbols from API if exchange is provided
  const {
    symbols: apiSymbols,
    isLoading,
    error,
  } = useSymbolsList(exchange, assetType);

  // Normalize value to array for internal processing
  const selectedSymbols = useMemo(() => {
    if (Array.isArray(value)) return value;
    return value ? [value] : [];
  }, [value]);

  // Build symbol options
  const symbolOptions = useMemo<SymbolOption[]>(() => {
    if (exchange && apiSymbols.length > 0) {
      // Use API symbols when exchange is specified and data is loaded
      return apiSymbols.map((s) => ({
        symbol: s.symbol,
        fullSymbol: s.full_symbol,
        marketType: detectMarketType(s.symbol),
      }));
    }

    // Fallback to preset symbols (use determined settlement currency)
    const options: SymbolOption[] = [];

    // Add crypto symbols with correct settlement currency
    POPULAR_CRYPTO_SYMBOLS.forEach((symbol) => {
      options.push({
        symbol,
        fullSymbol: `${symbol}/${settlement}:${settlement}`,
        marketType: "crypto_perp" as const,
      });
    });

    // Add forex symbols
    FOREX_SYMBOLS.forEach((symbol) => {
      options.push({
        symbol,
        fullSymbol: symbol,
        marketType: "forex" as const,
      });
    });

    // Add metals symbols
    METALS_SYMBOLS.forEach((symbol) => {
      options.push({
        symbol,
        fullSymbol: symbol,
        marketType: "metals" as const,
      });
    });

    return options;
  }, [exchange, apiSymbols, settlement]);

  // Filter symbols by tab and search
  const filteredOptions = useMemo(() => {
    let filtered = symbolOptions;

    // Filter by active tab
    if (showMarketTypeTabs) {
      filtered = filtered.filter(
        (s) => getTabCategory(s.marketType || "crypto_perp") === activeTab,
      );
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.symbol.toLowerCase().includes(query) ||
          s.fullSymbol.toLowerCase().includes(query),
      );
    }

    // Exclude already selected symbols in multiple mode
    if (mode === "multiple") {
      filtered = filtered.filter((s) => !selectedSymbols.includes(s.symbol));
    }

    return filtered;
  }, [
    symbolOptions,
    activeTab,
    searchQuery,
    selectedSymbols,
    mode,
    showMarketTypeTabs,
  ]);

  // Handle selection
  const handleSelect = useCallback(
    (symbol: string) => {
      if (mode === "single") {
        onChange(symbol);
        setOpen(false);
      } else {
        const newSelection = [...selectedSymbols];
        if (!newSelection.includes(symbol)) {
          if (newSelection.length >= maxSelections) return;
          newSelection.push(symbol);
        }
        onChange(newSelection);
      }
      setSearchQuery("");
    },
    [mode, onChange, selectedSymbols, maxSelections],
  );

  // Handle removal (multiple mode only)
  const handleRemove = useCallback(
    (symbol: string) => {
      if (mode === "multiple") {
        onChange(selectedSymbols.filter((s) => s !== symbol));
      }
    },
    [mode, onChange, selectedSymbols],
  );

  // Handle custom input
  const handleAddCustom = useCallback(() => {
    const symbol = customInput.toUpperCase().trim();
    if (symbol && !selectedSymbols.includes(symbol)) {
      if (mode === "single") {
        onChange(symbol);
        setOpen(false);
      } else if (selectedSymbols.length < maxSelections) {
        onChange([...selectedSymbols, symbol]);
      }
    }
    setCustomInput("");
  }, [customInput, selectedSymbols, mode, onChange, maxSelections]);

  // Get badge color by market type
  const getBadgeClass = (symbol: string) => {
    const mt = detectMarketType(symbol);
    if (mt === "forex")
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    if (mt === "metals")
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    return "";
  };

  // Size classes
  const sizeClasses = {
    sm: "h-8 text-xs",
    md: "h-10 text-sm",
    lg: "h-12 text-base",
  };

  // Placeholder text
  const placeholderText =
    placeholder ||
    (mode === "single" ? t("single.placeholder") : t("multiple.placeholder"));

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between", sizeClasses[size], className)}
        >
          {selectedSymbols.length > 0 ? (
            <span className="flex flex-wrap gap-1 truncate">
              {selectedSymbols.slice(0, 3).map((symbol) => (
                <Badge
                  key={symbol}
                  variant="secondary"
                  className={cn("text-xs px-1.5 py-0", getBadgeClass(symbol))}
                >
                  {symbol}
                  {mode === "multiple" && (
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemove(symbol);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          e.stopPropagation();
                          handleRemove(symbol);
                        }
                      }}
                      className="ml-0.5 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </span>
                  )}
                </Badge>
              ))}
              {selectedSymbols.length > 3 && (
                <Badge variant="secondary" className="text-xs px-1.5 py-0">
                  +{selectedSymbols.length - 3}
                </Badge>
              )}
            </span>
          ) : (
            <span className="text-muted-foreground">{placeholderText}</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={t("searchPlaceholder")}
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList className="max-h-[300px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  {t("loading")}
                </span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-6">
                <span className="text-sm text-destructive">
                  {t("loadFailed")}
                </span>
                <Button variant="ghost" size="sm" className="mt-2">
                  {t("retry")}
                </Button>
              </div>
            ) : (
              <>
                {showMarketTypeTabs && (
                  <Tabs
                    value={activeTab}
                    onValueChange={(v) => setActiveTab(v as typeof activeTab)}
                    className="w-full"
                  >
                    <TabsList className="grid w-full grid-cols-3 mx-2 mt-2">
                      <TabsTrigger value="crypto" className="text-xs">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        {t("marketType.crypto")}
                      </TabsTrigger>
                      <TabsTrigger value="forex" className="text-xs">
                        <DollarSign className="h-3 w-3 mr-1" />
                        {t("marketType.forex")}
                      </TabsTrigger>
                      <TabsTrigger value="metals" className="text-xs">
                        <Gem className="h-3 w-3 mr-1" />
                        {t("marketType.metals")}
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                )}

                {filteredOptions.length === 0 ? (
                  <CommandEmpty>{t("noResults")}</CommandEmpty>
                ) : (
                  <CommandGroup>
                    {filteredOptions.map((option) => (
                      <CommandItem
                        key={option.symbol}
                        value={option.symbol}
                        onSelect={() => handleSelect(option.symbol)}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedSymbols.includes(option.symbol)
                              ? "opacity-100"
                              : "opacity-0",
                          )}
                        />
                        <span className="font-medium">{option.symbol}</span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {option.fullSymbol}
                        </span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                )}

                {/* Custom Input */}
                {allowCustomInput && (
                  <div className="border-t p-2">
                    <div className="flex gap-2">
                      <Input
                        placeholder={t("customPlaceholder")}
                        value={customInput}
                        onChange={(e) =>
                          setCustomInput(e.target.value.toUpperCase())
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddCustom();
                          }
                        }}
                        className="h-8 text-xs"
                        maxLength={15}
                      />
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleAddCustom}
                        disabled={
                          !customInput.trim() ||
                          selectedSymbols.length >= maxSelections
                        }
                        className="h-8"
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export type { SymbolSelectorProps, SymbolSelectorMode, SymbolOption };
