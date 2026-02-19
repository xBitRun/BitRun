"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Plus,
  Search,
  Users,
  Loader2,
  Mail,
  Building2,
  Hash,
  Copy,
  Check,
  Filter,
  TrendingUp,
  Wallet,
  Bot,
  CreditCard,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  useChannels,
  useCreateChannel,
  useAdminUsers,
  useSetUserChannel,
} from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { format } from "date-fns";
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

// Role badge styling
function getRoleBadge(role: string) {
  const variants: Record<
    string,
    {
      variant: "default" | "secondary" | "destructive" | "outline";
      label: string;
    }
  > = {
    user: { variant: "outline", label: "user" },
    channel_admin: { variant: "secondary", label: "channelAdmin" },
    platform_admin: { variant: "default", label: "platformAdmin" },
  };
  return variants[role] || { variant: "outline", label: role };
}

export default function AdminChannelsPage() {
  const t = useTranslations("admin.channels");
  const commonT = useTranslations("common");
  const locale = useLocale();
  const { success, error } = useToast();
  const dateLocale = locale === "zh" ? zhCN : enUS;

  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  // Form state for creating invite code
  const [formData, setFormData] = useState({
    name: "",
    code: "",
    commission_rate: "0.3",
  });

  // Data hooks
  const {
    channels,
    isLoading: channelsLoading,
    refresh: refreshChannels,
  } = useChannels();
  const {
    users,
    isLoading: usersLoading,
    refresh: refreshUsers,
  } = useAdminUsers({
    search: searchQuery || undefined,
    role: roleFilter === "all" ? undefined : roleFilter,
    limit: 50,
  });
  const { trigger: createChannel, isMutating: isCreating } = useCreateChannel();
  const { trigger: setUserChannel } = useSetUserChannel();

  // Loading state
  const isLoading = channelsLoading || usersLoading;

  // Calculate platform statistics
  const platformStats = {
    totalChannels: channels.length,
    activeChannels: channels.filter((c) => c.status === "active").length,
    totalRevenue: channels.reduce((sum, c) => sum + c.total_revenue, 0),
    totalCommission: channels.reduce((sum, c) => sum + c.total_commission, 0),
    totalAccounts: channels.reduce((sum, c) => sum + c.total_accounts, 0),
    totalAgents: channels.reduce((sum, c) => sum + c.total_agents, 0),
  };

  // Handle create invite code (channel)
  const handleCreate = async () => {
    if (!formData.name || !formData.code) {
      error(commonT("validationError"));
      return;
    }

    try {
      await createChannel({
        name: formData.name,
        code: formData.code.toUpperCase(),
        commission_rate: parseFloat(formData.commission_rate) || 0.3,
      });
      success(t("createSuccess"));
      setCreateDialogOpen(false);
      setFormData({ name: "", code: "", commission_rate: "0.3" });
      refreshChannels();
    } catch {
      error(commonT("failed"));
    }
  };

  // Copy to clipboard
  const handleCopy = async (code: string) => {
    await navigator.clipboard.writeText(code);
    setCopied(code);
    success(t("copied"));
    setTimeout(() => setCopied(null), 2000);
  };

  // Filter users by search
  const filteredUsers = users.filter(
    (user) =>
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            {t("createInviteCode")}
          </Button>
        </div>
      </div>

      {/* Platform Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("platformStats.channels")}
            </CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {platformStats.activeChannels}
              <span className="text-sm text-muted-foreground ml-1">
                / {platformStats.totalChannels}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {t("platformStats.activeChannels")}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("platformStats.revenue")}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {formatCurrency(platformStats.totalRevenue)}
            </div>
            <p className="text-xs text-muted-foreground">
              {t("platformStats.platformRevenue")}:{" "}
              {formatCurrency(
                platformStats.totalRevenue - platformStats.totalCommission,
              )}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("platformStats.commission")}
            </CardTitle>
            <Wallet className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">
              {formatCurrency(platformStats.totalCommission)}
            </div>
            <p className="text-xs text-muted-foreground">
              {t("platformStats.totalCommission")}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Channels Table */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            {t("channelsList")}
          </CardTitle>
          <CardDescription>{t("channelsListDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          {channelsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : channels.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Building2 className="h-12 w-12 mb-4" />
              <p>{t("noInviteCodes")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("table.code")}</TableHead>
                    <TableHead>{t("table.name")}</TableHead>
                    <TableHead>{t("table.commissionRate")}</TableHead>
                    <TableHead>{t("table.status")}</TableHead>
                    <TableHead className="text-center">{t("table.accounts")}</TableHead>
                    <TableHead className="text-center">{t("table.agents")}</TableHead>
                    <TableHead className="text-right">{t("table.revenue")}</TableHead>
                    <TableHead className="text-right">{t("table.commission")}</TableHead>
                    <TableHead className="text-right">{t("table.pending")}</TableHead>
                    <TableHead>{t("table.createdAt")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {channels.map((channel) => (
                    <TableRow key={channel.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono font-bold bg-primary/10 px-2 py-0.5 rounded">
                            {channel.code}
                          </code>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleCopy(channel.code)}
                          >
                            {copied === channel.code ? (
                              <Check className="h-3 w-3 text-green-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{channel.name}</TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {(channel.commission_rate * 100).toFixed(0)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            channel.status === "active"
                              ? "default"
                              : channel.status === "suspended"
                                ? "secondary"
                                : "destructive"
                          }
                        >
                          {t(`status.${channel.status}`)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          <CreditCard className="h-3 w-3 text-muted-foreground" />
                          <span>{channel.total_accounts}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Bot className="h-3 w-3 text-muted-foreground" />
                          <span>{channel.total_agents}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium text-green-500">
                        {formatCurrency(channel.total_revenue)}
                      </TableCell>
                      <TableCell className="text-right text-blue-500">
                        {formatCurrency(channel.total_commission)}
                      </TableCell>
                      <TableCell className="text-right text-orange-500">
                        {formatCurrency(channel.pending_commission)}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {format(new Date(channel.created_at), "yyyy-MM-dd", {
                          locale: dateLocale,
                        })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Users Section */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            {t("allUsers")}
          </CardTitle>
          <CardDescription>{t("allUsersDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Search and Filter */}
          <div className="flex gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t("searchPlaceholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[150px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder={t("filterByRole")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("allRoles")}</SelectItem>
                <SelectItem value="user">{t("role.user")}</SelectItem>
                <SelectItem value="channel_admin">
                  {t("role.channelAdmin")}
                </SelectItem>
                <SelectItem value="platform_admin">
                  {t("role.platformAdmin")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Users Table */}
          {usersLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Users className="h-12 w-12 mb-4" />
              <p>{t("noUsers")}</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("table.email")}</TableHead>
                  <TableHead>{t("table.name")}</TableHead>
                  <TableHead>{t("table.role")}</TableHead>
                  <TableHead>{t("table.channel")}</TableHead>
                  <TableHead>{t("table.createdAt")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => {
                  const roleInfo = getRoleBadge(user.role);
                  return (
                    <TableRow key={user.id}>
                      <TableCell className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-muted-foreground" />
                        {user.email}
                      </TableCell>
                      <TableCell>{user.name || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={roleInfo.variant}>
                          {t(`role.${roleInfo.label}`)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {user.channel_code ? (
                          <div className="flex items-center gap-2">
                            <code className="text-sm bg-muted px-1.5 py-0.5 rounded">
                              {user.channel_code}
                            </code>
                            <span className="text-muted-foreground text-sm">
                              {user.channel_name}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {format(new Date(user.created_at), "yyyy-MM-dd", {
                          locale: dateLocale,
                        })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Invite Code Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>{t("createInviteCode")}</DialogTitle>
            <DialogDescription>
              {t("createInviteCodeDescription")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t("createDialog.name")}</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder={t("createDialog.namePlaceholder")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="code">{t("createDialog.code")}</Label>
              <div className="flex items-center gap-2">
                <Hash className="w-4 h-4 text-muted-foreground" />
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      code: e.target.value.toUpperCase(),
                    })
                  }
                  placeholder={t("createDialog.codePlaceholder")}
                  maxLength={6}
                  className="font-mono"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {t("createDialog.codeHint")}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="commission_rate">
                {t("createDialog.commissionRate")}
              </Label>
              <Input
                id="commission_rate"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={formData.commission_rate}
                onChange={(e) =>
                  setFormData({ ...formData, commission_rate: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                {t("createDialog.commissionRateHint")}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
            >
              {commonT("cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={isCreating}>
              {isCreating ? (
                <Loader2 className="w-4 w-4 mr-2 animate-spin" />
              ) : null}
              {commonT("confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
