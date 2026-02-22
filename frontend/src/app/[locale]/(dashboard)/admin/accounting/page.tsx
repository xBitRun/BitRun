"use client";

import { useTranslations } from "next-intl";
import {
  TrendingUp,
  DollarSign,
  Users,
  Building2,
  Loader2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

import { useChannels } from "@/hooks";
import {
  accountingApi,
  type PlatformAccountingOverview,
} from "@/lib/api/endpoints";
import useSWR from "swr";

// Format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(value);
}

// Format percentage
function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function AdminAccountingPage() {
  const t = useTranslations("admin.accounting");
  const { channels, isLoading: channelsLoading } = useChannels();

  // Platform overview
  const {
    data: platformOverview,
    isLoading: platformLoading,
  } = useSWR<PlatformAccountingOverview | null>(
    "/accounting/platform/overview",
    async () => {
      return accountingApi.getPlatformOverview();
    },
    {
      revalidateOnFocus: false,
    },
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      {platformLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : platformOverview ? (
        <>
          {/* Platform Stats */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalRevenue")}
                </CardTitle>
                <DollarSign className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatCurrency(platformOverview.total_revenue)}
                </div>
                <p className="text-xs text-muted-foreground">{t("allTime")}</p>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("platformRevenue")}
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">
                  {formatCurrency(platformOverview.platform_revenue)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatPercent(
                    platformOverview.platform_revenue /
                      platformOverview.total_revenue || 0,
                  )}
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalCommission")}
                </CardTitle>
                <Building2 className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-500">
                  {formatCurrency(platformOverview.total_commission)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatPercent(
                    platformOverview.total_commission /
                      platformOverview.total_revenue || 0,
                  )}
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalUsers")}
                </CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {platformOverview.total_users}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("registeredUsers")}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Channel Stats */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("totalChannels")}
                </CardTitle>
                <Building2 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {platformOverview.total_channels}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {t("activeChannels")}
                </CardTitle>
                <Building2 className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">
                  {platformOverview.active_channels}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Channel Breakdown */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                {t("channelBreakdown")}
              </CardTitle>
              <CardDescription>
                {t("channelBreakdownDescription")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {channelsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : channels.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <Building2 className="h-12 w-12 mb-4" />
                  <p>{t("noChannels")}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {channels.map((channel) => (
                    <div
                      key={channel.id}
                      className="flex items-center justify-between p-4 rounded-lg bg-muted/30"
                    >
                      <div>
                        <p className="font-medium">{channel.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {t("commissionRate")}:{" "}
                          {formatPercent(channel.commission_rate)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">
                          {formatCurrency(channel.total_revenue)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {t("users")}: {channel.total_users}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <TrendingUp className="h-16 w-16 mb-4" />
          <p>{t("noData")}</p>
        </div>
      )}
    </div>
  );
}
