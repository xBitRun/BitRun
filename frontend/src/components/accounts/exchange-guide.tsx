"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  BookOpen,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Shield,
  AlertTriangle,
  Info,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExchangeType } from "@/types";
import { ServerIPBadge } from "./server-ip-badge";

// Exchange registration and documentation links
const EXCHANGE_LINKS: Record<
  ExchangeType,
  { register: string; apiDocs?: string }
> = {
  binance: {
    register: "https://www.binance.com",
    apiDocs:
      "https://www.binance.com/zh-CN/support/faq/how-to-create-api-keys-on-binance-360002502072",
  },
  bybit: {
    register: "https://www.bybit.com",
    apiDocs:
      "https://www.bybit.com/zh-MY/help-center/article/How-to-create-your-API-key",
  },
  okx: {
    register: "https://www.okx.com",
    apiDocs: "https://www.okx.com/help/how-do-i-create-an-api-key",
  },
  hyperliquid: {
    register: "https://app.hyperliquid.xyz",
  },
  bitget: {
    register: "https://www.bitget.com",
    apiDocs: "https://www.bitget.com/academy/how-to-create-api-keys",
  },
  kucoin: {
    register: "https://www.kucoin.com",
    apiDocs: "https://www.kucoin.com/support/360015102174",
  },
  gate: {
    register: "https://www.gate.io",
    apiDocs: "https://www.gate.io/help/guide/api/16869/api-v4-key-management",
  },
};

interface ExchangeGuideProps {
  exchange: ExchangeType;
  className?: string;
}

function StepItem({ index, text }: { index: number; text: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary text-xs font-bold shrink-0 mt-0.5">
        {index}
      </div>
      <p className="text-sm text-foreground/80">{text}</p>
    </div>
  );
}

function PermissionItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2">
      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
      <span className="text-sm">{text}</span>
    </div>
  );
}

function NoteBox({
  children,
  variant = "info",
}: {
  children: React.ReactNode;
  variant?: "info" | "warning";
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 p-3 rounded-lg text-sm",
        variant === "warning"
          ? "bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300"
          : "bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300"
      )}
    >
      {variant === "warning" ? (
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      ) : (
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
      )}
      <div>{children}</div>
    </div>
  );
}

function BinanceGuide({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="space-y-4">
      {/* Steps */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <BookOpen className="w-4 h-4 text-primary" />
          {t("stepsTitle")}
        </h4>
        <div className="space-y-2">
          <StepItem index={1} text={t("binance.step1")} />
          <StepItem index={2} text={t("binance.step2")} />
          <StepItem index={3} text={t("binance.step3")} />
          <StepItem index={4} text={t("binance.step4")} />
          <StepItem index={5} text={t("binance.step5")} />
        </div>
      </div>

      {/* Permissions */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <Shield className="w-4 h-4 text-primary" />
          {t("permissionsTitle")}
        </h4>
        <div className="space-y-1.5 pl-1">
          <PermissionItem text={t("binance.perm1")} />
          <PermissionItem text={t("binance.perm2")} />
          <PermissionItem text={t("binance.perm3")} />
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <NoteBox variant="info">{t("binance.contractNote")}</NoteBox>
        <NoteBox variant="warning">{t("binance.ipWhitelist")}</NoteBox>
        <ServerIPBadge variant="full" />
      </div>
    </div>
  );
}

function BybitGuide({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="space-y-4">
      {/* Steps */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <BookOpen className="w-4 h-4 text-primary" />
          {t("stepsTitle")}
        </h4>
        <div className="space-y-2">
          <StepItem index={1} text={t("bybit.step1")} />
          <StepItem index={2} text={t("bybit.step2")} />
          <StepItem index={3} text={t("bybit.step3")} />
          <StepItem index={4} text={t("bybit.step4")} />
          <StepItem index={5} text={t("bybit.step5")} />
        </div>
      </div>

      {/* Permissions */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <Shield className="w-4 h-4 text-primary" />
          {t("permissionsTitle")}
        </h4>
        <div className="space-y-1.5 pl-1">
          <PermissionItem text={t("bybit.perm1")} />
          <PermissionItem text={t("bybit.perm2")} />
          <PermissionItem text={t("bybit.perm3")} />
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <NoteBox variant="warning">{t("bybit.proxyNote")}</NoteBox>
        <ServerIPBadge variant="full" />
      </div>
    </div>
  );
}

function OkxGuide({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="space-y-4">
      {/* Steps */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <BookOpen className="w-4 h-4 text-primary" />
          {t("stepsTitle")}
        </h4>
        <div className="space-y-2">
          <StepItem index={1} text={t("okx.step1")} />
          <StepItem index={2} text={t("okx.step2")} />
          <StepItem index={3} text={t("okx.step3")} />
          <StepItem index={4} text={t("okx.step4")} />
          <StepItem index={5} text={t("okx.step5")} />
          <StepItem index={6} text={t("okx.step6")} />
        </div>
      </div>

      {/* Permissions */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <Shield className="w-4 h-4 text-primary" />
          {t("permissionsTitle")}
        </h4>
        <div className="space-y-1.5 pl-1">
          <PermissionItem text={t("okx.perm1")} />
          <PermissionItem text={t("okx.perm2")} />
          <PermissionItem text={t("okx.perm3")} />
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <NoteBox variant="info">{t("okx.passphraseNote")}</NoteBox>
        <NoteBox variant="warning">{t("okx.proxyNote")}</NoteBox>
        <ServerIPBadge variant="full" />
      </div>
    </div>
  );
}

function HyperliquidGuide({
  t,
}: {
  t: ReturnType<typeof useTranslations>;
}) {
  return (
    <div className="space-y-4">
      {/* Overview */}
      <NoteBox variant="info">{t("hyperliquid.title")}</NoteBox>

      {/* Private Key Guide */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold">{t("stepsTitle")}</h4>
        <div className="space-y-3 pl-1">
          <div className="p-3 rounded-lg bg-muted/40 border border-border/50">
            <Badge variant="outline" className="mb-1.5 text-xs">
              Private Key
            </Badge>
            <p className="text-sm text-foreground/80">
              {t("hyperliquid.privateKeyGuide")}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-muted/40 border border-border/50">
            <Badge variant="outline" className="mb-1.5 text-xs">
              Mnemonic
            </Badge>
            <p className="text-sm text-foreground/80">
              {t("hyperliquid.mnemonicGuide")}
            </p>
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <NoteBox variant="warning">{t("hyperliquid.securityNote")}</NoteBox>
        <NoteBox variant="info">{t("hyperliquid.fundingNote")}</NoteBox>
      </div>
    </div>
  );
}

function GenericCexGuide({
  t,
  exchangeKey,
  hasPassphrase = false,
}: {
  t: ReturnType<typeof useTranslations>;
  exchangeKey: string;
  hasPassphrase?: boolean;
}) {
  return (
    <div className="space-y-4">
      {/* Steps */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <BookOpen className="w-4 h-4 text-primary" />
          {t("stepsTitle")}
        </h4>
        <div className="space-y-2">
          <StepItem index={1} text={t(`${exchangeKey}.step1`)} />
          <StepItem index={2} text={t(`${exchangeKey}.step2`)} />
          <StepItem index={3} text={t(`${exchangeKey}.step3`)} />
          <StepItem index={4} text={t(`${exchangeKey}.step4`)} />
        </div>
      </div>

      {/* Permissions */}
      <div className="space-y-1.5">
        <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-2">
          <Shield className="w-4 h-4 text-primary" />
          {t("permissionsTitle")}
        </h4>
        <div className="space-y-1.5 pl-1">
          <PermissionItem text={t(`${exchangeKey}.perm1`)} />
          <PermissionItem text={t(`${exchangeKey}.perm2`)} />
          <PermissionItem text={t(`${exchangeKey}.perm3`)} />
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        {hasPassphrase && (
          <NoteBox variant="info">{t(`${exchangeKey}.passphraseNote`)}</NoteBox>
        )}
        <NoteBox variant="warning">{t(`${exchangeKey}.note`)}</NoteBox>
        <ServerIPBadge variant="full" />
      </div>
    </div>
  );
}

export function ExchangeGuide({ exchange, className }: ExchangeGuideProps) {
  const t = useTranslations("accounts.guide");
  const [isOpen, setIsOpen] = useState(false);

  const links = EXCHANGE_LINKS[exchange];

  const guideContent: Record<ExchangeType, React.ReactNode> = {
    binance: <BinanceGuide t={t} />,
    bybit: <BybitGuide t={t} />,
    okx: <OkxGuide t={t} />,
    hyperliquid: <HyperliquidGuide t={t} />,
    bitget: <GenericCexGuide t={t} exchangeKey="bitget" hasPassphrase />,
    kucoin: <GenericCexGuide t={t} exchangeKey="kucoin" hasPassphrase />,
    gate: <GenericCexGuide t={t} exchangeKey="gate" />,
  };

  return (
    <Card
      className={cn(
        "border-primary/20 bg-primary/2 overflow-hidden transition-all",
        className
      )}
    >
      {/* Header - always visible */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">{t("title")}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {isOpen ? t("hideGuide") : t("showGuide")}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expandable content */}
      {isOpen && (
        <CardContent className="pt-0 pb-4 px-4">
          <div className="border-t border-border/50 pt-4 space-y-4">
            {/* Action links */}
            <div className="flex flex-wrap gap-2">
              <a
                href={links.register}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" size="sm" className="h-8 text-xs">
                  <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                  {t("registerLink")}
                </Button>
              </a>
              {links.apiDocs && (
                <a
                  href={links.apiDocs}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline" size="sm" className="h-8 text-xs">
                    <BookOpen className="w-3.5 h-3.5 mr-1.5" />
                    {t("officialDocs")}
                  </Button>
                </a>
              )}
            </div>

            {/* Exchange-specific guide */}
            {guideContent[exchange]}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
