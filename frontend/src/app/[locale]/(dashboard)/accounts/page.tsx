"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Plus,
  MoreHorizontal,
  ExternalLink,
  RefreshCw,
  Trash2,
  Wallet,
  TestTube,
  Loader2,
} from "lucide-react";
import {
  ListPageSkeleton,
  ListPageError,
  ListPageEmpty,
} from "@/components/list-page";
import { useToast } from "@/components/ui/toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useAccounts, useAccountBalance } from "@/hooks";
import type { AccountResponse } from "@/lib/api";
import type { ExchangeType } from "@/types";
import { accountsApi } from "@/lib/api";

const exchangeLogos: Record<ExchangeType, string> = {
  hyperliquid: "🔷",
  binance: "🟡",
  bybit: "🟠",
  okx: "⬛",
};

const exchangeNames: Record<ExchangeType, string> = {
  hyperliquid: "Hyperliquid",
  binance: "Binance",
  bybit: "Bybit",
  okx: "OKX",
};

interface AccountCardProps {
  account: AccountResponse;
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
  t: ReturnType<typeof useTranslations>;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function AccountCard({ account, onDelete, onTest, t }: AccountCardProps) {
  const [isTesting, setIsTesting] = useState(false);

  // Fetch balance only for connected accounts
  const {
    data: balance,
    isLoading: isLoadingBalance,
    error: balanceError,
    mutate: refreshBalance
  } = useAccountBalance(account.is_connected ? account.id : null);

  const handleTest = async () => {
    setIsTesting(true);
    try {
      await onTest(account.id);
    } finally {
      setIsTesting(false);
    }
  };

  const handleRefreshBalance = async () => {
    if (account.is_connected) {
      await refreshBalance();
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {exchangeLogos[account.exchange as ExchangeType] || "📊"}
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                {account.name}
                {account.is_testnet && (
                  <Badge variant="outline" className="text-xs">
                    <TestTube className="w-3 h-3 mr-1" />
                    {t("card.testnet")}
                  </Badge>
                )}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {exchangeNames[account.exchange as ExchangeType] || account.exchange}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleTest} disabled={isTesting}>
                {isTesting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                {t("menu.testConnection")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleRefreshBalance} disabled={!account.is_connected}>
                <RefreshCw className="w-4 h-4 mr-2" />
                {t("menu.refreshBalance")}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <ExternalLink className="w-4 h-4 mr-2" />
                {t("menu.openExchange")}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(account.id)}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t("menu.removeAccount")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Connection Status */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
          <span className="text-sm text-muted-foreground">{t("card.status")}</span>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                account.is_connected ? "bg-[var(--profit)]" : "bg-[var(--loss)]"
              )}
            />
            <span
              className={cn(
                "text-sm font-medium",
                account.is_connected ? "text-[var(--profit)]" : "text-[var(--loss)]"
              )}
            >
              {account.is_connected ? t("card.connected") : t("card.disconnected")}
            </span>
          </div>
        </div>

        {/* Balance Section */}
        <div className="p-4 rounded-lg bg-muted/30 border border-border/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {t("card.totalEquity")}
              </span>
            </div>
            {isLoadingBalance && (
              <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
            )}
          </div>

          {!account.is_connected ? (
            <p className="text-lg font-medium text-muted-foreground">
              {t("card.notConnected")}
            </p>
          ) : isLoadingBalance ? (
            <Skeleton className="h-8 w-32" />
          ) : balanceError ? (
            <p className="text-sm text-destructive">
              {t("card.balanceError")}
            </p>
          ) : balance ? (
            <>
              <p className="text-2xl font-bold font-mono">
                {formatCurrency(balance.equity)}
              </p>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    {t("card.availableBalance")}
                  </span>
                  <span className="font-mono">
                    {formatCurrency(balance.available_balance)}
                  </span>
                </div>
                {balance.unrealized_pnl !== 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("card.unrealizedPnl")}
                    </span>
                    <span className={cn(
                      "font-mono font-medium",
                      balance.unrealized_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"
                    )}>
                      {balance.unrealized_pnl >= 0 ? "+" : ""}
                      {formatCurrency(balance.unrealized_pnl)}
                    </span>
                  </div>
                )}
                {balance.positions.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("card.positions")}
                    </span>
                    <span className="font-medium">
                      {balance.positions.length}
                    </span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-2xl font-bold font-mono">—</p>
          )}
        </div>

        {/* Last synced */}
        <p className="text-xs text-muted-foreground">
          {account.last_synced_at
            ? `${t("card.lastSynced")} ${new Date(account.last_synced_at).toLocaleString()}`
            : `${t("card.added")} ` +
              " " +
              new Date(account.created_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
        </p>
      </CardContent>
    </Card>
  );
}

export default function AccountsPage() {
  const t = useTranslations("accounts");
  const toast = useToast();

  const { accounts, error, isLoading, refresh } = useAccounts();

  const handleDeleteAccount = async (id: string) => {
    if (!confirm(t("confirmDelete"))) return;

    try {
      await accountsApi.delete(id);
      refresh();
      toast.success(t("toast.removeSuccess"));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.removeFailed");
      toast.error(t("toast.removeFailed"), message);
    }
  };

  const handleTestConnection = async (id: string) => {
    try {
      const result = await accountsApi.testConnection(id);
      if (result.success) {
        toast.success(t("toast.connectionSuccess"), result.message);
      } else {
        toast.error(t("toast.connectionFailed"), result.message);
      }
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.testFailed");
      toast.error(t("toast.testFailed"), message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link href="/accounts/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t("addAccount")}
          </Button>
        </Link>
      </div>

      {/* Info Card */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="flex items-center gap-4 py-4">
          <div className="p-3 rounded-full bg-primary/10">
            <Wallet className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{t("info.title")}</h3>
            <p className="text-sm text-muted-foreground">{t("info.description")}</p>
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {isLoading && <ListPageSkeleton />}

      {/* Error */}
      {error && (
        <ListPageError
          message={error.message || t("error.loadFailed")}
          onRetry={() => refresh()}
          retryLabel={t("retry")}
        />
      )}

      {/* Empty - no accounts */}
      {!isLoading && !error && accounts.length === 0 && (
        <ListPageEmpty
          icon={Wallet}
          title={t("empty.title")}
          description={t("empty.description")}
          actionLabel={t("empty.createFirst")}
          actionHref="/accounts/new"
          actionIcon={Plus}
        />
      )}

      {/* Account Cards + Add card when has data */}
      {!isLoading && !error && accounts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              onDelete={handleDeleteAccount}
              onTest={handleTestConnection}
              t={t}
            />
          ))}

          <Link href="/accounts/new">
            <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex flex-col items-center justify-center h-full min-h-[280px] text-muted-foreground hover:text-foreground transition-colors">
                <div className="p-4 rounded-full bg-muted/30 mb-4">
                  <Plus className="w-8 h-8" />
                </div>
                <p className="font-medium">{t("addCard.title")}</p>
                <p className="text-sm text-center mt-1">{t("addCard.subtitle")}</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      )}
    </div>
  );
}
