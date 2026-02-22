"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { MarketSnapshotItem, AccountSnapshotItem } from "@/lib/api/endpoints";

// Generic translation function type
type TFunc = (key: string) => string;

// ==================== Account Snapshot Section ====================

export function AccountSnapshotSection({
  snapshot,
  t,
}: {
  snapshot: AccountSnapshotItem;
  t: TFunc;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button className="flex items-center gap-2 text-sm font-semibold hover:text-primary transition-colors w-full text-left">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {t("decisions.accountSnapshot.title")}
          <Badge variant="outline" className="ml-2 text-xs font-mono">
            ${snapshot.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </Badge>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-3 p-4 rounded-lg bg-muted/20 border border-border/30 space-y-4">
          {/* Account Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">{t("decisions.accountSnapshot.equity")}</span>
              <p className="font-mono font-semibold">${snapshot.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t("decisions.accountSnapshot.availableBalance")}</span>
              <p className="font-mono">${snapshot.available_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t("decisions.accountSnapshot.marginUsed")}</span>
              <p className="font-mono">${snapshot.total_margin_used.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({snapshot.margin_usage_percent.toFixed(1)}%)</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t("decisions.accountSnapshot.unrealizedPnl")}</span>
              <p className={cn("font-mono font-semibold", snapshot.unrealized_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]")}>
                ${snapshot.unrealized_pnl >= 0 ? "+" : ""}{snapshot.unrealized_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">{t("decisions.accountSnapshot.positionCount")}</span>
              <p className="font-mono">{snapshot.position_count}</p>
            </div>
          </div>

          {/* Positions */}
          {snapshot.positions.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {t("decisions.accountSnapshot.positions")}
              </h5>
              <div className="space-y-2">
                {snapshot.positions.map((pos, idx) => (
                  <div key={idx} className="p-3 rounded bg-muted/30 border border-border/20">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold">{pos.symbol}</span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            pos.side === "long"
                              ? "text-[var(--profit)] border-[var(--profit)]/30"
                              : "text-[var(--loss)] border-[var(--loss)]/30"
                          )}
                        >
                          {pos.side.toUpperCase()}
                        </Badge>
                        <Badge variant="secondary" className="text-xs">{pos.leverage}x</Badge>
                      </div>
                      <span className={cn(
                        "font-mono text-sm font-semibold",
                        pos.unrealized_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"
                      )}>
                        {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl.toFixed(2)} ({pos.unrealized_pnl_percent >= 0 ? "+" : ""}{pos.unrealized_pnl_percent.toFixed(2)}%)
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">{t("decisions.accountSnapshot.sizeValue")}</span>
                        <p className="font-mono">${pos.size_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">{t("decisions.accountSnapshot.sizeQty")}</span>
                        <p className="font-mono">{pos.size}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">{t("decisions.accountSnapshot.entry")}</span>
                        <p className="font-mono">${pos.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">{t("decisions.accountSnapshot.leverage")}</span>
                        <p className="font-mono">{pos.leverage}x</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">{t("decisions.accountSnapshot.liquidation")}</span>
                        <p className="font-mono">{pos.liquidation_price != null ? `$${pos.liquidation_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "N/A"}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {snapshot.positions.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("decisions.accountSnapshot.noPositions")}</p>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ==================== Market Data Snapshot Section ====================

export function MarketSnapshotSection({
  snapshot,
  t,
}: {
  snapshot: MarketSnapshotItem[];
  t: TFunc;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button className="flex items-center gap-2 text-sm font-semibold hover:text-primary transition-colors w-full text-left">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {t("decisions.marketSnapshot.title")}
          <Badge variant="outline" className="ml-2 text-xs">
            {snapshot.length} {snapshot.length === 1 ? t("decisions.marketSnapshot.symbol") : t("decisions.marketSnapshot.symbols")}
          </Badge>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-3 space-y-4">
          {snapshot.map((item) => {
            // Calculate spread percentage
            const spreadPct = item.current.mid_price > 0
              ? ((item.current.ask_price - item.current.bid_price) / item.current.mid_price) * 100
              : 0;

            // Calculate average 24h funding rate (3 most recent = ~24h)
            const fundingSlice = item.funding_history?.slice(0, 3) ?? [];
            const avgFunding24h = fundingSlice.length > 0
              ? fundingSlice.reduce((sum, f) => sum + f.rate, 0) / fundingSlice.length
              : null;

            return (
              <div
                key={item.symbol}
                className="p-4 rounded-lg bg-muted/20 border border-border/30 space-y-4"
              >
                {/* Header: Symbol + Exchange */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base font-bold">{item.symbol}</span>
                    {item.exchange_name && (
                      <Badge variant="outline" className="text-xs capitalize">
                        {item.exchange_name}
                      </Badge>
                    )}
                  </div>
                  <span className="text-lg font-mono font-semibold break-all text-right">
                    ${item.current.mid_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Price Details */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">{t("decisions.marketSnapshot.bid")}</span>
                    <p className="font-mono">${item.current.bid_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t("decisions.marketSnapshot.ask")}</span>
                    <p className="font-mono">${item.current.ask_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t("decisions.marketSnapshot.spread")}</span>
                    <p className="font-mono">{spreadPct.toFixed(3)}%</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t("decisions.marketSnapshot.volume24h")}</span>
                    <p className="font-mono">${item.current.volume_24h.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t("decisions.marketSnapshot.fundingRate")}</span>
                    <p className="font-mono">
                      {item.current.funding_rate != null
                        ? `${(item.current.funding_rate * 100).toFixed(4)}%`
                        : "N/A"}
                    </p>
                  </div>
                  {avgFunding24h !== null && (
                    <div>
                      <span className="text-muted-foreground">{t("decisions.marketSnapshot.avgFunding24h")}</span>
                      <p className="font-mono">
                        {(avgFunding24h * 100).toFixed(4)}%{" "}
                          <span className={cn(
                          "text-sm",
                          avgFunding24h > 0 ? "text-[var(--profit)]" : avgFunding24h < 0 ? "text-[var(--loss)]" : "text-muted-foreground"
                        )}>
                          ({avgFunding24h > 0 ? t("decisions.marketSnapshot.bullishBias") : avgFunding24h < 0 ? t("decisions.marketSnapshot.bearishBias") : t("decisions.marketSnapshot.neutral")})
                        </span>
                      </p>
                    </div>
                  )}
                </div>

                {/* Technical Indicators by Timeframe */}
                {Object.keys(item.indicators).length > 0 && (
                  <div>
                    <h5 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      {t("decisions.marketSnapshot.indicators")}
                    </h5>
                    <div className="space-y-2">
                      {Object.entries(item.indicators).map(([tf, ind]) => (
                        <div key={tf} className="p-3 rounded bg-muted/30 border border-border/20">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <Badge variant="secondary" className="text-xs font-mono">
                              {tf.toUpperCase()}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                ind.ema_trend === "bullish"
                                  ? "text-[var(--profit)]"
                                  : ind.ema_trend === "bearish"
                                  ? "text-[var(--loss)]"
                                  : "text-muted-foreground"
                              )}
                            >
                              EMA: {ind.ema_trend}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                ind.rsi_signal === "overbought" || ind.rsi_signal === "bearish"
                                  ? "text-[var(--loss)]"
                                  : ind.rsi_signal === "oversold" || ind.rsi_signal === "bullish"
                                  ? "text-[var(--profit)]"
                                  : "text-muted-foreground"
                              )}
                            >
                              RSI: {ind.rsi != null ? ind.rsi.toFixed(1) : "N/A"} ({ind.rsi_signal})
                            </Badge>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                ind.macd_signal === "bullish"
                                  ? "text-[var(--profit)]"
                                  : ind.macd_signal === "bearish"
                                  ? "text-[var(--loss)]"
                                  : "text-muted-foreground"
                              )}
                            >
                              MACD: {ind.macd_signal}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                            {/* MACD Values */}
                            {ind.macd && (ind.macd.macd !== 0 || ind.macd.signal !== 0) && (
                              <>
                                <div>
                                  <span className="text-muted-foreground">{t("decisions.marketSnapshot.macdLine")}</span>
                                  <p className="font-mono">{ind.macd.macd.toFixed(4)}</p>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">{t("decisions.marketSnapshot.signalLine")}</span>
                                  <p className="font-mono">{ind.macd.signal.toFixed(4)}</p>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">{t("decisions.marketSnapshot.histogram")}</span>
                                  <p className={cn("font-mono", ind.macd.histogram > 0 ? "text-[var(--profit)]" : ind.macd.histogram < 0 ? "text-[var(--loss)]" : "")}>
                                    {ind.macd.histogram > 0 ? "+" : ""}{ind.macd.histogram.toFixed(4)}
                                  </p>
                                </div>
                              </>
                            )}
                            {ind.atr != null && (
                              <div>
                                <span className="text-muted-foreground">ATR</span>
                                <p className="font-mono">{ind.atr.toFixed(2)}</p>
                              </div>
                            )}
                            {ind.bollinger && ind.bollinger.upper > 0 && (
                              <>
                                <div>
                                  <span className="text-muted-foreground">BB Upper</span>
                                  <p className="font-mono">{ind.bollinger.upper.toFixed(2)}</p>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">BB Middle</span>
                                  <p className="font-mono">{ind.bollinger.middle.toFixed(2)}</p>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">BB Lower</span>
                                  <p className="font-mono">{ind.bollinger.lower.toFixed(2)}</p>
                                </div>
                              </>
                            )}
                            {Object.entries(ind.ema).map(([period, value]) => (
                              <div key={period}>
                                <span className="text-muted-foreground">EMA({period})</span>
                                <p className="font-mono">{Number(value).toFixed(2)}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent K-lines */}
                {Object.keys(item.klines).length > 0 && (() => {
                  const tfKeys = Object.keys(item.klines);
                  const primaryTf = tfKeys.includes("1h") ? "1h" : tfKeys.includes("15m") ? "15m" : tfKeys[0];
                  const klines = item.klines[primaryTf];
                  if (!klines || klines.length === 0) return null;

                  return (
                    <div>
                      <h5 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        {t("decisions.marketSnapshot.recentKlines")} ({primaryTf.toUpperCase()})
                      </h5>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-muted-foreground border-b border-border/30">
                              <th className="text-left py-1 pr-3 font-medium">{t("decisions.marketSnapshot.time")}</th>
                              <th className="text-right py-1 px-2 font-medium">{t("decisions.marketSnapshot.open")}</th>
                              <th className="text-right py-1 px-2 font-medium">{t("decisions.marketSnapshot.high")}</th>
                              <th className="text-right py-1 px-2 font-medium">{t("decisions.marketSnapshot.low")}</th>
                              <th className="text-right py-1 px-2 font-medium">{t("decisions.marketSnapshot.close")}</th>
                              <th className="text-right py-1 px-2 font-medium">{t("decisions.marketSnapshot.volume")}</th>
                              <th className="text-right py-1 pl-2 font-medium">{t("decisions.marketSnapshot.change")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {klines.map((k, idx) => {
                              const changePct = k.open > 0 ? ((k.close - k.open) / k.open) * 100 : 0;
                              const isBullish = k.close >= k.open;
                              const timeStr = new Date(k.timestamp).toLocaleString(undefined, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
                              return (
                                <tr key={idx} className="border-b border-border/10">
                                  <td className="py-1 pr-3 font-mono text-muted-foreground">{timeStr}</td>
                                  <td className="text-right py-1 px-2 font-mono">{k.open.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                  <td className="text-right py-1 px-2 font-mono">{k.high.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                  <td className="text-right py-1 px-2 font-mono">{k.low.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                  <td className="text-right py-1 px-2 font-mono">{k.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                  <td className="text-right py-1 px-2 font-mono">{k.volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                  <td className={cn("text-right py-1 pl-2 font-mono", isBullish ? "text-[var(--profit)]" : "text-[var(--loss)]")}>
                                    {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()}

                {/* Funding Rate History */}
                {item.funding_history && item.funding_history.length > 0 && (
                  <div>
                    <h5 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      {t("decisions.marketSnapshot.fundingHistory")}
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {item.funding_history.slice(0, 8).map((fh, idx) => {
                        const timeStr = new Date(fh.timestamp).toLocaleString(undefined, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
                        return (
                          <div key={idx} className="px-2 py-1 rounded bg-muted/30 border border-border/20 text-sm">
                            <span className="text-muted-foreground">{timeStr}</span>
                            <span className={cn("ml-2 font-mono", fh.rate > 0 ? "text-[var(--profit)]" : fh.rate < 0 ? "text-[var(--loss)]" : "text-muted-foreground")}>
                              {(fh.rate * 100).toFixed(4)}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
