"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CreditCard,
  History,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Plus,
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
import { Label } from "@/components/ui/label";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useRechargeOrders, useCreateRechargeOrder, useWallet } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import {  format } from "date-fns";
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

// Order status badge
function getStatusBadge(status: string) {
  const variants: Record<
    string,
    {
      variant: "default" | "secondary" | "destructive" | "outline";
      icon: React.ReactNode;
    }
  > = {
    pending: { variant: "outline", icon: <Clock className="w-3 h-3" /> },
    paid: { variant: "secondary", icon: <CheckCircle className="w-3 h-3" /> },
    completed: {
      variant: "default",
      icon: <CheckCircle className="w-3 h-3" />,
    },
    failed: { variant: "destructive", icon: <XCircle className="w-3 h-3" /> },
    refunded: { variant: "outline", icon: <AlertCircle className="w-3 h-3" /> },
  };
  return variants[status] || variants.pending;
}

// Preset amounts
const PRESET_AMOUNTS = [100, 500, 1000, 5000];

export default function RechargePage() {
  const t = useTranslations("wallet");
  const commonT = useTranslations("common");
  const router = useRouter();
  const locale = useLocale();
  const { success, error } = useToast();

  // Data hooks
  const { wallet } = useWallet();
  const {
    orders,
    isLoading: ordersLoading,
    refresh: refreshOrders,
  } = useRechargeOrders({ limit: 10 });
  const { trigger: createOrder, isMutating: isCreating } =
    useCreateRechargeOrder();

  // Form state
  const [amount, setAmount] = useState<string>("");
  const [bonusAmount, setBonusAmount] = useState<string>("0");
  const [dialogOpen, setDialogOpen] = useState(false);

  // Date locale
  const dateLocale = locale === "zh" ? zhCN : enUS;

  // Handle create order
  const handleCreateOrder = async () => {
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      error(commonT("validationError"));
      return;
    }

    try {
      await createOrder({
        amount: amountNum,
        bonus_amount: parseFloat(bonusAmount) || 0,
      });
      success(t("recharge.success"));
      setDialogOpen(false);
      setAmount("");
      setBonusAmount("0");
      refreshOrders();
    } catch {
      error(commonT("failed"));
    }
  };

  // Handle preset amount click
  const handlePresetAmount = (value: number) => {
    setAmount(value.toString());
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/wallet")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gradient">
            {t("recharge.title")}
          </h1>
          <p className="text-muted-foreground">{t("recharge.description")}</p>
        </div>
      </div>

      {/* Current Balance */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">{t("balance")}</p>
              <p className="text-3xl font-bold">
                {formatCurrency(wallet?.balance ?? 0)}
              </p>
            </div>
            <CreditCard className="h-12 w-12 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="create" className="space-y-6">
        <TabsList>
          <TabsTrigger value="create" className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            {t("recharge.submit")}
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="w-4 h-4" />
            {t("recharge.orders")}
          </TabsTrigger>
        </TabsList>

        {/* Create Order Tab */}
        <TabsContent value="create">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle>{t("recharge.title")}</CardTitle>
              <CardDescription>{t("recharge.description")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Preset amounts */}
              <div className="space-y-2">
                <Label>{t("recharge.amount")}</Label>
                <div className="flex flex-wrap gap-2">
                  {PRESET_AMOUNTS.map((preset) => (
                    <Button
                      key={preset}
                      variant={
                        amount === preset.toString() ? "default" : "outline"
                      }
                      onClick={() => handlePresetAmount(preset)}
                    >
                      {formatCurrency(preset)}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Custom amount */}
              <div className="space-y-2">
                <Label htmlFor="amount">
                  {t("recharge.amountPlaceholder")}
                </Label>
                <Input
                  id="amount"
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder={t("recharge.amountPlaceholder")}
                  min="1"
                />
              </div>

              {/* Bonus amount (usually hidden for regular users) */}
              <div className="space-y-2">
                <Label htmlFor="bonus">{t("recharge.bonus")}</Label>
                <Input
                  id="bonus"
                  type="number"
                  value={bonusAmount}
                  onChange={(e) => setBonusAmount(e.target.value)}
                  placeholder="0"
                  min="0"
                />
              </div>

              {/* Total */}
              {amount && parseFloat(amount) > 0 && (
                <div className="p-4 rounded-lg bg-muted/30">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">
                      {t("recharge.amount")}
                    </span>
                    <span className="font-medium">
                      {formatCurrency(parseFloat(amount))}
                    </span>
                  </div>
                  {parseFloat(bonusAmount) > 0 && (
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-muted-foreground">
                        {t("recharge.bonus")}
                      </span>
                      <span className="font-medium text-green-500">
                        +{formatCurrency(parseFloat(bonusAmount))}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between items-center mt-2 pt-2 border-t border-border">
                    <span className="font-medium">{t("totalBalance")}</span>
                    <span className="text-xl font-bold">
                      {formatCurrency(
                        parseFloat(amount) + (parseFloat(bonusAmount) || 0),
                      )}
                    </span>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    className="w-full"
                    disabled={!amount || parseFloat(amount) <= 0}
                  >
                    <CreditCard className="w-4 h-4 mr-2" />
                    {t("recharge.submit")}
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{t("recharge.title")}</DialogTitle>
                    <DialogDescription>
                      {t("recharge.description")}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="p-4 rounded-lg bg-muted/30 text-center">
                      <p className="text-sm text-muted-foreground mb-2">
                        {t("recharge.amount")}
                      </p>
                      <p className="text-3xl font-bold">
                        {formatCurrency(
                          parseFloat(amount) + (parseFloat(bonusAmount) || 0),
                        )}
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground text-center">
                      创建订单后，请联系客服完成支付确认。
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => setDialogOpen(false)}
                      >
                        {commonT("cancel")}
                      </Button>
                      <Button
                        className="flex-1"
                        onClick={handleCreateOrder}
                        disabled={isCreating}
                      >
                        {isCreating ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : null}
                        {commonT("confirm")}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Order History Tab */}
        <TabsContent value="history">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                {t("recharge.orders")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ordersLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : orders.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <Clock className="h-12 w-12 mb-4" />
                  <p>{t("recharge.noOrders")}</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("recharge.orderNo")}</TableHead>
                      <TableHead>{t("recharge.amount")}</TableHead>
                      <TableHead>{t("recharge.status.pending")}</TableHead>
                      <TableHead>{t("recharge.createdAt")}</TableHead>
                      <TableHead>{t("recharge.completedAt")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => {
                      const statusInfo = getStatusBadge(order.status);
                      return (
                        <TableRow key={order.id}>
                          <TableCell className="font-mono text-sm">
                            {order.order_no}
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
                            <Badge
                              variant={statusInfo.variant}
                              className="gap-1"
                            >
                              {statusInfo.icon}
                              {t(`recharge.status.${order.status}`)}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {format(
                              new Date(order.created_at),
                              "yyyy-MM-dd HH:mm",
                              {
                                locale: dateLocale,
                              },
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {order.completed_at
                              ? format(
                                  new Date(order.completed_at),
                                  "yyyy-MM-dd HH:mm",
                                  {
                                    locale: dateLocale,
                                  },
                                )
                              : "-"}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
