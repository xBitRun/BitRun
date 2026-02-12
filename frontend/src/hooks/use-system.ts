/**
 * System Hooks
 *
 * Server system information (outbound IP, etc.)
 */

import useSWR from "swr";
import { systemApi } from "@/lib/api";
import type { OutboundIPResponse } from "@/lib/api";

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
