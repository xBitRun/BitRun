"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  CreditCard,
  Search,
  Loader2,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Filter,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import {  useAdminRechargeOrders } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { format } from "date-fns";
import { zhCN, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";
import { rechargeApi } from "@/lib/api/endpoints";

// Format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(value);
}

// Order status badge
function getStatusBadge(status: string) {
  const variants: Record<
    string,
    {
      variant: "default" | "secondary" | "destructive" | "outline";
      icon: React.ReactNode;
      label: string;
    }
  > = {
    pending: {
      variant: "outline",
      icon: <Clock className="w-3 h-3" />,
      label: "pending",
    },
    paid: {
      variant: "secondary",
      icon: <CheckCircle className="w-3 h-3" />,
      label: "paid",
    },
    completed: {
      variant: "default",
      icon: <CheckCircle className="w-3 h-3" />,
      label: "completed",
    },
    failed: {
      variant: "destructive",
      icon: <XCircle className="w-3 h-3" />,
      label: "failed",
    },
    refunded: {
      variant: "outline",
      icon: <AlertCircle className="w-3 h-3" />,
      label: "refunded",
    },
  };
  return variants[status] || variants.pending;
}

export default function AdminRechargePage() {
  const t = useTranslations("admin.recharge");
  const commonT = useTranslations("common");
  const walletT = useTranslations("wallet");
  const locale = useLocale();
  const { success, error } = useToast();
  const dateLocale = locale === "zh" ? zhCN : enUS;

  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  // Data hooks
  const { orders, isLoading, refresh } = useAdminRechargeOrders({ limit: 100 });

  // Filter orders
  const filteredOrders = orders.filter((order) => {
    const searchLower = searchQuery.toLowerCase();
    const matchesSearch =
      order.order_no.toLowerCase().includes(searchLower) ||
      order.user_id.toLowerCase().includes(searchLower) ||
      (order.user_email?.toLowerCase().includes(searchLower) ?? false) ||
      (order.user_name?.toLowerCase().includes(searchLower) ?? false);
    const matchesStatus =
      statusFilter === "all" || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Handle confirm order
  const handleConfirm = async () => {
    if (!selectedOrder) return;

    setIsConfirming(true);
    try {
      await rechargeApi.adminConfirm(selectedOrder);
      success(t("confirmSuccess"));
      setConfirmDialogOpen(false);
      setSelectedOrder(null);
      refresh();
    } catch {
      error(commonT("failed"));
    } finally {
      setIsConfirming(false);
    }
  };

  // Stats
  const pendingCount = orders.filter((o) => o.status === "pending").length;
  const pendingAmount = orders
    .filter((o) => o.status === "pending")
    .reduce((sum, o) => sum + o.amount + (o.bonus_amount || 0), 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("pendingOrders")}
            </CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingCount}</div>
            <p className="text-xs text-muted-foreground">
              {t("pendingAmount")}: {formatCurrency(pendingAmount)}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("totalOrders")}
            </CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{orders.length}</div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t("totalAmount")}
            </CardTitle>
            <CreditCard className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {formatCurrency(
                orders
                  .filter((o) => o.status === "completed")
                  .reduce((sum, o) => sum + o.amount, 0),
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder={t("filterStatus")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{commonT("all")}</SelectItem>
            <SelectItem value="pending">
              {walletT("recharge.status.pending")}
            </SelectItem>
            <SelectItem value="paid">
              {walletT("recharge.status.paid")}
            </SelectItem>
            <SelectItem value="completed">
              {walletT("recharge.status.completed")}
            </SelectItem>
            <SelectItem value="failed">
              {walletT("recharge.status.failed")}
            </SelectItem>
            <SelectItem value="refunded">
              {walletT("recharge.status.refunded")}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Orders Table */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <CreditCard className="h-12 w-12 mb-4" />
              <p>
                {searchQuery || statusFilter !== "all"
                  ? t("noResults")
                  : t("noOrders")}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("table.orderNo")}</TableHead>
                  <TableHead>{t("table.user")}</TableHead>
                  <TableHead>{t("table.amount")}</TableHead>
                  <TableHead>{t("table.status")}</TableHead>
                  <TableHead>{t("table.createdAt")}</TableHead>
                  <TableHead>{t("table.completedAt")}</TableHead>
                  <TableHead className="w-[100px]">
                    {t("table.actions")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOrders.map((order) => {
                  const statusInfo = getStatusBadge(order.status);
                  return (
                    <TableRow key={order.id}>
                      <TableCell className="font-mono text-sm">
                        {order.order_no}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium text-sm">
                            {order.user_name || order.user_email || "-"}
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            {order.user_email ||
                              `${order.user_id.slice(0, 8)}...`}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <span className="font-medium">
                            {formatCurrency(order.amount)}
                          </span>
                          {order.bonus_amount > 0 && (
                            <span className="text-green-500 text-sm ml-1">
                              +{formatCurrency(order.bonus_amount)}
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusInfo.variant} className="gap-1">
                          {statusInfo.icon}
                          {walletT(`recharge.status.${statusInfo.label}`)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {format(
                          new Date(order.created_at),
                          "yyyy-MM-dd HH:mm",
                          { locale: dateLocale },
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {order.completed_at
                          ? format(
                              new Date(order.completed_at),
                              "yyyy-MM-dd HH:mm",
                              { locale: dateLocale },
                            )
                          : "-"}
                      </TableCell>
                      <TableCell>
                        {(order.status === "pending" ||
                          order.status === "paid") && (
                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedOrder(order.id);
                              setConfirmDialogOpen(true);
                            }}
                          >
                            {t("confirm")}
                          </Button>
                        )}
                        {order.status !== "pending" &&
                          order.status !== "paid" && (
                            <span className="text-muted-foreground text-sm">
                              -
                            </span>
                          )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Confirm Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("confirmDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("confirmDialog.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              {t("confirmDialog.warning")}
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDialogOpen(false)}
            >
              {commonT("cancel")}
            </Button>
            <Button onClick={handleConfirm} disabled={isConfirming}>
              {isConfirming ? (
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
