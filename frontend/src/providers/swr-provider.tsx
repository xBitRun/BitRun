"use client";

import { SWRConfig } from "swr";
import { ReactNode } from "react";
import { api } from "@/lib/api";
import { logger } from "@/lib/logger";

interface SWRProviderProps {
  children: ReactNode;
}

export function SWRProvider({ children }: SWRProviderProps) {
  return (
    <SWRConfig
      value={{
        // Default fetcher using our API client
        fetcher: (url: string) => api.get(url),

        // Global configuration
        revalidateOnFocus: false,
        revalidateOnReconnect: true,
        dedupingInterval: 2000,
        errorRetryCount: 3,

        // Error handling - only log in development
        onError: (error, key) => {
          logger.error(`SWR Error [${key}]:`, error);
        },
      }}
    >
      {children}
    </SWRConfig>
  );
}
