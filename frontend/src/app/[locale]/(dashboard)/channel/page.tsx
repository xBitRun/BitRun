"use client";


import { useTranslations } from "next-intl";
import {
  Building2,
  Users,
  Wallet,
  TrendingUp,
  Clock,
  Loader2,
  Mail,
  Phone,
  User,
  Calendar,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

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
import {
  useMyChannel,
  useMyChannelUsers,
  useMyChannelWallet,
  useMyChannelStatistics,
  useMyChannelAccounting,
} from "@/hooks";
import { formatDistanceToNow, format } from "date-fns";
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

// Channel status badge
function getStatusBadge(status: string) {
  const variants: Record<
    string,
    {
      variant: "default" | "secondary" | "destructive" | "outline";
      label: string;
    }
  > = {
    active: { variant: "default", label: "active" },
    suspended: { variant: "secondary", label: "suspended" },
    closed: { variant: "destructive", label: "closed" },
  };
  return variants[status] || { variant: "outline", label: status };
}

export default function ChannelPage() {
  const t = useTranslations("channel");
  const locale = useLocale();
  const dateLocale = locale === "zh" ? zhCN : enUS;

  // Data hooks
  const {
    channel,
    isLoading: channelLoading,
  } = useMyChannel();
  const {
    users,
    isLoading: usersLoading,
  } = useMyChannelUsers({ limit: 50 });
  const {
    wallet,
    isLoading: walletLoading,
  } = useMyChannelWallet();
  const { statistics } = useMyChannelStatistics();
  const { overview, isLoading: accountingLoading } = useMyChannelAccounting();

  // No channel access
  if (!channelLoading && !channel) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <Building2 className="h-16 w-16 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold mb-2">{t("noChannel")}</h2>
        <p className="text-muted-foreground">{t("noChannelDescription")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      {channelLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* Channel Info Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="w-5 h-5" />
                  {channel?.name}
                </CardTitle>
                <Badge variant={getStatusBadge(channel?.status || "").variant}>
                  {t(`status.${getStatusBadge(channel?.status || "").label}`)}
                </Badge>
              </div>
              <CardDescription>
                {t("code")}: {channel?.code}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {channel?.contact_name && (
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{channel.contact_name}</span>
                  </div>
                )}
                {channel?.contact_email && (
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{channel.contact_email}</span>
                  </div>
                )}
                {channel?.contact_phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{channel.contact_phone}</span>
                  </div>
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {t("createdAt")}:{" "}
                    {format(new Date(channel?.created_at || ""), "yyyy-MM-dd", {
                      locale: dateLocale,
                    })}
                  </div>
                  <div>
                    {t("commissionRate")}:{" "}
                    <span className="text-primary font-medium">
                      {((channel?.commission_rate || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Stats Grid */}
          <div className="grid gap-4 md:grid-cols-4">
            {/* Total Users */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalUsers")}
                </CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statistics?.total_users ?? channel?.total_users ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("activeUsers")}: {statistics?.active_users ?? 0}
                </p>
              </CardContent>
            </Card>

            {/* Wallet Balance */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("walletBalance")}
                </CardTitle>
                <Wallet className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {walletLoading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">
                      {formatCurrency(wallet?.balance ?? 0)}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t("pendingCommission")}:{" "}
                      {formatCurrency(statistics?.pending_commission ?? 0)}
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Total Commission */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalCommission")}
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                {walletLoading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                ) : (
                  <>
                    <div className="text-2xl font-bold text-green-500">
                      {formatCurrency(statistics?.total_commission ?? 0)}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t("periodCommission")}:{" "}
                      {formatCurrency(statistics?.period_commission ?? 0)}
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Total Revenue */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalRevenue")}
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">
                  {formatCurrency(statistics?.total_revenue ?? 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("availableBalance")}:{" "}
                  {formatCurrency(statistics?.available_balance ?? 0)}
                </p>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="users" className="space-y-6">
            <TabsList>
              <TabsTrigger value="users" className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                {t("users.title")}
              </TabsTrigger>
              <TabsTrigger value="wallet" className="flex items-center gap-2">
                <Wallet className="w-4 h-4" />
                {t("wallet.title")}
              </TabsTrigger>
              <TabsTrigger
                value="accounting"
                className="flex items-center gap-2"
              >
                <TrendingUp className="w-4 h-4" />
                {t("accounting.title")}
              </TabsTrigger>
            </TabsList>

            {/* Users Tab */}
            <TabsContent value="users">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    {t("users.title")}
                  </CardTitle>
                  <CardDescription>{t("users.description")}</CardDescription>
                </CardHeader>
                <CardContent>
                  {usersLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : users.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                      <Users className="h-12 w-12 mb-4" />
                      <p>{t("users.noData")}</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("users.email")}</TableHead>
                          <TableHead>{t("users.name")}</TableHead>
                          <TableHead>{t("users.registeredAt")}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {users.map((user) => (
                          <TableRow key={user.id}>
                            <TableCell>{user.email}</TableCell>
                            <TableCell>{user.name || "-"}</TableCell>
                            <TableCell className="text-muted-foreground">
                              {formatDistanceToNow(new Date(user.created_at), {
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
            </TabsContent>

            {/* Wallet Tab */}
            <TabsContent value="wallet">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Wallet className="w-5 h-5" />
                    {t("wallet.title")}
                  </CardTitle>
                  <CardDescription>{t("wallet.description")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {walletLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : wallet ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="p-6 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
                        <p className="text-sm text-muted-foreground mb-2">
                          {t("wallet.balance")}
                        </p>
                        <p className="text-3xl font-bold">
                          {formatCurrency(wallet.balance)}
                        </p>
                      </div>
                      <div className="p-6 rounded-xl bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">
                          {t("wallet.pendingCommission")}
                        </p>
                        <p className="text-3xl font-bold text-yellow-500">
                          {formatCurrency(wallet.pending_commission)}
                        </p>
                      </div>
                      <div className="p-6 rounded-xl bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">
                          {t("wallet.frozenBalance")}
                        </p>
                        <p className="text-3xl font-bold">
                          {formatCurrency(wallet.frozen_balance)}
                        </p>
                      </div>
                      <div className="p-6 rounded-xl bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">
                          {t("wallet.totalWithdrawn")}
                        </p>
                        <p className="text-3xl font-bold">
                          {formatCurrency(wallet.total_withdrawn)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                      <Wallet className="h-12 w-12 mb-4" />
                      <p>{t("wallet.noData")}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Accounting Tab */}
            <TabsContent value="accounting">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    {t("accounting.title")}
                  </CardTitle>
                  <CardDescription>
                    {t("accounting.description")}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {accountingLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : overview ? (
                    <div className="space-y-6">
                      {/* Revenue Summary */}
                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="p-4 rounded-lg bg-muted/30">
                          <p className="text-sm text-muted-foreground">
                            {t("accounting.totalRevenue")}
                          </p>
                          <p className="text-2xl font-bold">
                            {formatCurrency(overview.total_revenue)}
                          </p>
                        </div>
                        <div className="p-4 rounded-lg bg-muted/30">
                          <p className="text-sm text-muted-foreground">
                            {t("accounting.totalCommission")}
                          </p>
                          <p className="text-2xl font-bold text-green-500">
                            {formatCurrency(overview.total_commission)}
                          </p>
                        </div>
                        <div className="p-4 rounded-lg bg-muted/30">
                          <p className="text-sm text-muted-foreground">
                            {t("periodCommission")}
                          </p>
                          <p className="text-2xl font-bold text-blue-500">
                            {formatCurrency(overview.period_commission)}
                          </p>
                        </div>
                      </div>

                      {/* Balance Summary */}
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="p-4 rounded-lg bg-muted/30">
                          <p className="text-sm text-muted-foreground">
                            {t("availableBalance")}
                          </p>
                          <p className="text-xl font-bold">
                            {formatCurrency(overview.available_balance)}
                          </p>
                        </div>
                        <div className="p-4 rounded-lg bg-muted/30">
                          <p className="text-sm text-muted-foreground">
                            {t("accounting.activeUsers")}
                          </p>
                          <p className="text-xl font-bold">
                            {overview.active_users}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                      <Clock className="h-12 w-12 mb-4" />
                      <p>{t("accounting.noData")}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
