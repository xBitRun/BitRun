"use client";

import { useEffect, useRef, memo, useId } from "react";
import { cn } from "@/lib/utils";

interface TradingViewChartProps {
  symbol?: string;
  interval?: string;
  className?: string;
}

/**
 * TradingView Advanced Chart Widget wrapper.
 * Uses the official TradingView embed script — zero backend dependency.
 * Height is controlled via the parent container / className (h-full by default).
 */
function TradingViewChartInner({
  symbol = "BINANCE:BTCUSDT",
  interval = "60",
  className,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reactId = useId();
  const widgetId = `tradingview_${reactId.replace(/:/g, '_')}`;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Clear any previous widget
    container.innerHTML = "";

    // Create the widget container div
    const widgetDiv = document.createElement("div");
    widgetDiv.id = widgetId;
    widgetDiv.style.height = "100%";
    widgetDiv.style.width = "100%";
    container.appendChild(widgetDiv);

    // Inject the TradingView script
    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval,
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1", // candlestick
      locale: "en",
      backgroundColor: "rgba(0, 0, 0, 0)",
      gridColor: "rgba(255, 255, 255, 0.04)",
      hide_top_toolbar: false,
      hide_legend: false,
      allow_symbol_change: true,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: "https://www.tradingview.com",
    });

    widgetDiv.appendChild(script);

    return () => {
      // Cleanup
      if (container) {
        container.innerHTML = "";
      }
    };
  }, [symbol, interval, widgetId]);

  return (
    <div
      ref={containerRef}
      className={cn("h-full w-full", className)}
    />
  );
}

export const TradingViewChart = memo(TradingViewChartInner);
