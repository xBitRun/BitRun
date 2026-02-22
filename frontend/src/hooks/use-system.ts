/**
 * System Hooks
 *
 * Server system information (outbound IP, etc.)
 */

import useSWR from "swr";
import { dataApi, systemApi } from "@/lib/api";
import type { OutboundIPResponse, PricePrefetchStatsResponse } from "@/lib/api";

export function useOutboundIP() {
  const { data, error, isLoading } = useSWR<OutboundIPResponse>(
    "system-outbound-ip",
    () => systemApi.getOutboundIP(),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 60_000, // Dedupe for 60s — IP rarely changes
    }
  );

  return {
    ip: data?.ip ?? null,
    source: data?.source ?? null,
    isLoading,
    error,
  };
}

export function usePricePrefetchStatus() {
  const { data, error, isLoading } = useSWR<PricePrefetchStatsResponse>(
    "price-prefetch-stats",
    () => dataApi.getPricePrefetchStats(),
    {
      refreshInterval: 10_000,
      revalidateOnFocus: true,
      dedupingInterval: 5_000,
    }
  );

  const streamHits = data?.stream_hits ?? 0;
  const streamFallbacks = data?.stream_fallbacks ?? 0;
  const streamTotal = streamHits + streamFallbacks;

  let mode: "unknown" | "ws" | "mixed" | "rest" = "unknown";
  if (streamTotal > 0) {
    if (streamHits === 0) mode = "rest";
    else if (streamFallbacks === 0) mode = "ws";
    else mode = streamHits >= streamFallbacks ? "mixed" : "rest";
  } else if (data?.running) {
    mode = "mixed";
  }

  return {
    data,
    mode,
    isLoading,
    error,
  };
}
