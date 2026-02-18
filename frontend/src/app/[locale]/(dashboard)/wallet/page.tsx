"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  RefreshCw,
  Copy,
  Check,
  History,
  Gift,
  Clock,
  TrendingUp,
  TrendingDown,
  Loader2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useWallet, useWalletTransactions, useInviteInfo } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { formatDistanceToNow } from "date-fns";
import { zhCN, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";

// Format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(value);
}

// Transaction type badge variant
function getTypeBadgeVariant(
  type: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (type) {
    case "recharge":
    case "gift":
      return "default";
    case "consume":
      return "destructive";
    case "refund":
    case "adjustment":
      return "secondary";
    default:
      return "outline";
  }
}

export default function WalletPage() {
  const t = useTranslations("wallet");
  const commonT = useTranslations("common");
  const router = useRouter();
  const locale = useLocale();
  const { success } = useToast();

  // Data hooks
  const {
    wallet,
    isLoading: walletLoading,
    refresh: refreshWallet,
  } = useWallet();
  const { inviteInfo, isLoading: inviteLoading } = useInviteInfo();
  const [transactionType, setTransactionType] = useState<string>("all");
  const {
    transactions,
    isLoading: transactionsLoading,
    refresh: refreshTransactions,
  } = useWalletTransactions({
    types: transactionType === "all" ? undefined : transactionType,
    limit: 20,
  });

  // Copy state
  const [copied, setCopied] = useState(false);

  // Loading states
  const isLoading = walletLoading || inviteLoading;

  // Copy invite code
  const handleCopyInviteCode = async () => {
    if (inviteInfo?.invite_code) {
      await navigator.clipboard.writeText(inviteInfo.invite_code);
      setCopied(true);
      success(t("invite.copied"));
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Refresh all data
  const handleRefresh = async () => {
    await Promise.all([refreshWallet(), refreshTransactions()]);
  };

  // Date locale
  const dateLocale = locale === "zh" ? zhCN : enUS;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
            />
            {commonT("retry")}
          </Button>
          <Button onClick={() => router.push("/wallet/recharge")}>
            <ArrowUpRight className="w-4 h-4 mr-2" />
            {t("recharge.title")}
          </Button>
        </div>
      </div>

      {/* Balance Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Available Balance */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("balance")}
            </CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {walletLoading ? (
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {formatCurrency(wallet?.balance ?? 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {t("frozenBalance")}:{" "}
                  {formatCurrency(wallet?.frozen_balance ?? 0)}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Total Recharged */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("totalRecharged")}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            {walletLoading ? (
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold text-green-500">
                {formatCurrency(wallet?.total_recharged ?? 0)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Total Consumed */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("totalConsumed")}
            </CardTitle>
            <TrendingDown className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            {walletLoading ? (
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold text-orange-500">
                {formatCurrency(wallet?.total_consumed ?? 0)}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Invite Code Card */}
      {inviteInfo?.invite_code && (
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gift className="w-5 h-5" />
              {t("invite.title")}
            </CardTitle>
            <CardDescription>{t("invite.description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm text-muted-foreground">
                  {t("invite.myCode")}
                </p>
                <p className="text-xl font-mono font-bold">
                  {inviteInfo.invite_code}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">
                    {t("invite.invited")}
                  </p>
                  <p className="text-lg font-bold">
                    {inviteInfo.total_invited}
                  </p>
                </div>
                <Button variant="outline" onClick={handleCopyInviteCode}>
                  {copied ? (
                    <Check className="w-4 h-4 mr-2" />
                  ) : (
                    <Copy className="w-4 h-4 mr-2" />
                  )}
                  {copied ? commonT("copied") : commonT("copy")}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transaction History */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="w-5 h-5" />
            {t("transactions.title")}
          </CardTitle>
          <CardDescription>
            {/* Filter tabs */}
            <Tabs
              value={transactionType}
              onValueChange={setTransactionType}
              className="mt-4"
            >
              <TabsList>
                <TabsTrigger value="all">{commonT("all")}</TabsTrigger>
                <TabsTrigger value="recharge">
                  {t("transactions.types.recharge")}
                </TabsTrigger>
                <TabsTrigger value="consume">
                  {t("transactions.types.consume")}
                </TabsTrigger>
                <TabsTrigger value="refund">
                  {t("transactions.types.refund")}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transactionsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : transactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Clock className="h-12 w-12 mb-4" />
              <p>{t("transactions.noData")}</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("transactions.type")}</TableHead>
                  <TableHead>{t("transactions.amount")}</TableHead>
                  <TableHead>{t("transactions.balance")}</TableHead>
                  <TableHead>{t("transactions.description")}</TableHead>
                  <TableHead>{t("transactions.time")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell>
                      <Badge variant={getTypeBadgeVariant(tx.type)}>
                        {t(`transactions.types.${tx.type}`)}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className={
                        tx.type === "recharge" ||
                        tx.type === "gift" ||
                        tx.type === "refund"
                          ? "text-green-500 font-medium"
                          : "text-orange-500 font-medium"
                      }
                    >
                      {tx.type === "recharge" ||
                      tx.type === "gift" ||
                      tx.type === "refund"
                        ? "+"
                        : "-"}
                      {formatCurrency(tx.amount)}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <span className="text-muted-foreground">
                          {formatCurrency(tx.balance_before)}
                        </span>
                        {" → "}
                        <span className="font-medium">
                          {formatCurrency(tx.balance_after)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {tx.description || "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDistanceToNow(new Date(tx.created_at), {
                        addSuffix: true,
                        locale: dateLocale,
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
