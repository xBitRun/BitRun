"use client";

import { ReactNode } from "react";
import { SWRProvider } from "./swr-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ToastProvider } from "@/components/ui/toast";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <SWRProvider>
      <TooltipProvider>
        <ToastProvider>
          {children}
        </ToastProvider>
      </TooltipProvider>
    </SWRProvider>
  );
}
