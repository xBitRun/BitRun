"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Gift,
  Copy,
  Check,
  Users,
  Share2,
  Loader2,
  Link2,
  Mail,
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
import { useInviteInfo } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { useBrand } from "@/lib/brand-context";

export default function InvitePage() {
  const t = useTranslations("wallet");
  const commonT = useTranslations("common");
  const { success } = useToast();
  const { shortName } = useBrand();

  // Data hooks
  const { inviteInfo, isLoading } = useInviteInfo();

  // Copy state
  const [copied, setCopied] = useState<"code" | "link" | null>(null);

  // Generate invite link
  const inviteLink = inviteInfo?.invite_code
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/register?invite=${inviteInfo.invite_code}`
    : "";

  // Copy to clipboard
  const handleCopy = async (type: "code" | "link", value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(type);
    success(t("invite.copied"));
    setTimeout(() => setCopied(null), 2000);
  };

  // Share via Web Share API
  const handleShare = async () => {
    if (navigator.share && inviteInfo?.invite_code) {
      try {
        await navigator.share({
          title: `${shortName} 邀请注册`,
          text: `使用我的邀请码 ${inviteInfo.invite_code} 注册 ${shortName}`,
          url: inviteLink,
        });
      } catch (err) {
        // User cancelled or share failed
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gradient">
          {t("invite.title")}
        </h1>
        <p className="text-muted-foreground">{t("invite.description")}</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Invite Code Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Gift className="w-5 h-5" />
                {t("invite.myCode")}
              </CardTitle>
              <CardDescription>{t("invite.description")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Invite Code Display */}
              <div className="p-6 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
                <p className="text-sm text-muted-foreground mb-2">
                  {t("invite.myCode")}
                </p>
                <div className="flex items-center justify-between">
                  <p className="text-3xl font-mono font-bold tracking-wider">
                    {inviteInfo?.invite_code || "-"}
                  </p>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() =>
                      handleCopy("code", inviteInfo?.invite_code || "")
                    }
                    disabled={!inviteInfo?.invite_code}
                  >
                    {copied === "code" ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Invite Link */}
              {inviteInfo?.invite_code && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">{t("invite.share")}</p>
                  <div className="flex gap-2">
                    <Input
                      value={inviteLink}
                      readOnly
                      className="bg-muted/50 font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handleCopy("link", inviteLink)}
                    >
                      {copied === "link" ? (
                        <Check className="w-4 h-4 text-green-500" />
                      ) : (
                        <Link2 className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* Share Button */}
              {typeof navigator !== "undefined" && "share" in navigator && (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleShare}
                  disabled={!inviteInfo?.invite_code}
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  {t("invite.share")}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Stats Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                {t("invite.invited")}
              </CardTitle>
              <CardDescription>通过您的邀请码注册的用户统计</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Total Invited */}
              <div className="p-6 rounded-xl bg-muted/30 text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  {t("invite.invited")}
                </p>
                <p className="text-4xl font-bold">
                  {inviteInfo?.total_invited ?? 0}
                </p>
              </div>

              {/* Referrer Info */}
              {inviteInfo?.referrer_id && (
                <div className="p-4 rounded-lg bg-muted/30">
                  <p className="text-sm text-muted-foreground mb-1">
                    {t("invite.referrer")}
                  </p>
                  <p className="font-mono text-sm">{inviteInfo.referrer_id}</p>
                </div>
              )}

              {/* Channel Info */}
              {inviteInfo?.channel_id && (
                <div className="p-4 rounded-lg bg-muted/30">
                  <p className="text-sm text-muted-foreground mb-1">
                    {t("invite.channel")}
                  </p>
                  <p className="font-mono text-sm">{inviteInfo.channel_id}</p>
                </div>
              )}

              {/* How it works */}
              <div className="space-y-3 pt-4 border-t border-border">
                <h4 className="font-medium">邀请规则</h4>
                <ul className="text-sm text-muted-foreground space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-primary">1.</span>
                    分享您的邀请码给朋友
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary">2.</span>
                    朋友注册时填写您的邀请码
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary">3.</span>
                    注册成功后，您和您的朋友都可能获得奖励
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
