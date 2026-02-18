"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Building2,
  Plus,
  Search,
  MoreHorizontal,
  Loader2,
  RefreshCw,
  Mail,
  Phone,
  User,
  CheckCircle,
  XCircle,
  PauseCircle,
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useChannels, useCreateChannel, useUpdateChannelStatus } from "@/hooks";
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

// Channel status badge
function getStatusBadge(status: string) {
  const variants: Record<
    string,
    {
      variant: "default" | "secondary" | "destructive" | "outline";
      icon: React.ReactNode;
      label: string;
    }
  > = {
    active: {
      variant: "default",
      icon: <CheckCircle className="w-3 h-3" />,
      label: "active",
    },
    suspended: {
      variant: "secondary",
      icon: <PauseCircle className="w-3 h-3" />,
      label: "suspended",
    },
    closed: {
      variant: "destructive",
      icon: <XCircle className="w-3 h-3" />,
      label: "closed",
    },
  };
  return variants[status] || { variant: "outline", icon: null, label: status };
}

export default function AdminChannelsPage() {
  const t = useTranslations("admin.channels");
  const commonT = useTranslations("common");
  const locale = useLocale();
  const { success, error } = useToast();
  const dateLocale = locale === "zh" ? zhCN : enUS;

  // Data hooks
  const { channels, isLoading, refresh } = useChannels();
  const { trigger: createChannel, isMutating: isCreating } = useCreateChannel();
  const { trigger: updateStatus, isMutating: isUpdatingStatus } =
    useUpdateChannelStatus();

  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState<string>("");

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    code: "",
    commission_rate: "0.3",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
  });

  // Filter channels
  const filteredChannels = channels.filter(
    (channel) =>
      channel.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      channel.code.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Handle create channel
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
        contact_name: formData.contact_name || undefined,
        contact_email: formData.contact_email || undefined,
        contact_phone: formData.contact_phone || undefined,
      });
      success(t("createSuccess"));
      setCreateDialogOpen(false);
      setFormData({
        name: "",
        code: "",
        commission_rate: "0.3",
        contact_name: "",
        contact_email: "",
        contact_phone: "",
      });
      refresh();
    } catch (err) {
      error(commonT("failed"));
    }
  };

  // Handle update status
  const handleUpdateStatus = async () => {
    if (!selectedChannel || !newStatus) return;

    try {
      await updateStatus({
        channelId: selectedChannel,
        status: newStatus as "active" | "suspended" | "closed",
      });
      success(t("statusUpdateSuccess"));
      setStatusDialogOpen(false);
      setSelectedChannel(null);
      setNewStatus("");
      refresh();
    } catch (err) {
      error(commonT("failed"));
    }
  };

  // Open status dialog
  const openStatusDialog = (channelId: string, currentStatus: string) => {
    setSelectedChannel(channelId);
    setNewStatus(currentStatus);
    setStatusDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => refresh()}
            disabled={isLoading}
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
            />
            {commonT("retry")}
          </Button>
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            {t("create")}
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t("searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Channels Table */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredChannels.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Building2 className="h-12 w-12 mb-4" />
              <p>{searchQuery ? t("noResults") : t("noChannels")}</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("table.name")}</TableHead>
                  <TableHead>{t("table.code")}</TableHead>
                  <TableHead>{t("table.status")}</TableHead>
                  <TableHead>{t("table.commissionRate")}</TableHead>
                  <TableHead>{t("table.users")}</TableHead>
                  <TableHead>{t("table.revenue")}</TableHead>
                  <TableHead>{t("table.contact")}</TableHead>
                  <TableHead>{t("table.createdAt")}</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredChannels.map((channel) => {
                  const statusInfo = getStatusBadge(channel.status);
                  return (
                    <TableRow key={channel.id}>
                      <TableCell className="font-medium">
                        {channel.name}
                      </TableCell>
                      <TableCell>
                        <code className="text-sm bg-muted px-1.5 py-0.5 rounded">
                          {channel.code}
                        </code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusInfo.variant} className="gap-1">
                          {statusInfo.icon}
                          {t(`status.${statusInfo.label}`)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {(channel.commission_rate * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell>{channel.total_users}</TableCell>
                      <TableCell>
                        {formatCurrency(channel.total_revenue)}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {channel.contact_name && (
                            <div className="flex items-center gap-1">
                              <User className="w-3 h-3" />
                              {channel.contact_name}
                            </div>
                          )}
                          {channel.contact_email && (
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Mail className="w-3 h-3" />
                              {channel.contact_email}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {format(new Date(channel.created_at), "yyyy-MM-dd", {
                          locale: dateLocale,
                        })}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() =>
                                openStatusDialog(channel.id, channel.status)
                              }
                            >
                              {t("actions.changeStatus")}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() =>
                                openStatusDialog(channel.id, "suspended")
                              }
                              className="text-orange-500"
                            >
                              {t("actions.suspend")}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                openStatusDialog(channel.id, "closed")
                              }
                              className="text-destructive"
                            >
                              {t("actions.close")}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Channel Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{t("createDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("createDialog.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid gap-4 md:grid-cols-2">
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
                  maxLength={20}
                />
              </div>
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
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="contact_name">
                  {t("createDialog.contactName")}
                </Label>
                <Input
                  id="contact_name"
                  value={formData.contact_name}
                  onChange={(e) =>
                    setFormData({ ...formData, contact_name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_phone">
                  {t("createDialog.contactPhone")}
                </Label>
                <Input
                  id="contact_phone"
                  value={formData.contact_phone}
                  onChange={(e) =>
                    setFormData({ ...formData, contact_phone: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_email">
                {t("createDialog.contactEmail")}
              </Label>
              <Input
                id="contact_email"
                type="email"
                value={formData.contact_email}
                onChange={(e) =>
                  setFormData({ ...formData, contact_email: e.target.value })
                }
              />
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
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {commonT("confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Status Update Dialog */}
      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("statusDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("statusDialog.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex gap-2">
              {["active", "suspended", "closed"].map((status) => {
                const info = getStatusBadge(status);
                return (
                  <Button
                    key={status}
                    variant={newStatus === status ? "default" : "outline"}
                    onClick={() => setNewStatus(status)}
                    className="flex-1"
                  >
                    <Badge variant={info.variant} className="gap-1 mr-2">
                      {info.icon}
                    </Badge>
                    {t(`status.${info.label}`)}
                  </Button>
                );
              })}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setStatusDialogOpen(false)}
            >
              {commonT("cancel")}
            </Button>
            <Button onClick={handleUpdateStatus} disabled={isUpdatingStatus}>
              {isUpdatingStatus ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {commonT("confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
