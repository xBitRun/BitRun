"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Copy, Check, Globe, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useOutboundIP } from "@/hooks";
import { cn } from "@/lib/utils";

interface ServerIPBadgeProps {
  /** Compact mode: inline badge only. Full mode: shows card with description */
  variant?: "compact" | "full";
  className?: string;
}

export function ServerIPBadge({
  variant = "compact",
  className,
}: ServerIPBadgeProps) {
  const t = useTranslations("accounts.serverIP");
  const { ip, isLoading, error } = useOutboundIP();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!ip) return;
    try {
      await navigator.clipboard.writeText(ip);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for insecure contexts
      const textarea = document.createElement("textarea");
      textarea.value = ip;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
        <Loader2 className="w-3 h-3 animate-spin" />
        <span>{t("loading")}</span>
      </div>
    );
  }

  if (error || !ip) {
    return (
      <div className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
        <Globe className="w-3 h-3" />
        <span>{t("unavailable")}</span>
      </div>
    );
  }

  if (variant === "compact") {
    return (
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={handleCopy}
              className={cn(
                "inline-flex items-center gap-1.5 group",
                className
              )}
            >
              <Badge
                variant="outline"
                className="font-mono text-xs gap-1.5 px-2.5 py-0.5 cursor-pointer hover:bg-primary/10 transition-colors border-primary/30"
              >
                <Globe className="w-3 h-3 text-primary" />
                {ip}
                {copied ? (
                  <Check className="w-3 h-3 text-emerald-500" />
                ) : (
                  <Copy className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
                )}
              </Badge>
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-xs">
            {copied ? t("copied") : t("clickToCopy")}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Full variant — inline row, visually aligned with NoteBox siblings
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-muted/50 border border-border/50",
        className
      )}
    >
      <div className="flex items-center gap-2 min-w-0 text-xs text-muted-foreground">
        <Globe className="w-3.5 h-3.5 shrink-0" />
        <span className="truncate">{t("title")}</span>
      </div>
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 font-mono text-xs text-foreground/80 hover:text-foreground px-2 py-1 rounded-md hover:bg-muted transition-colors shrink-0"
            >
              {ip}
              {copied ? (
                <Check className="w-3 h-3 text-emerald-500" />
              ) : (
                <Copy className="w-3 h-3 text-muted-foreground" />
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-xs">
            {copied ? t("copied") : t("clickToCopy")}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
