"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Gift,
  Copy,
  Check,
  Share2,
  Loader2,
  Link2,
  Building2,
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
  const { success } = useToast();
  const { shortName } = useBrand();

  // Data hooks
  const { inviteInfo, isLoading } = useInviteInfo();

  // Copy state
  const [copied, setCopied] = useState<"code" | "link" | null>(null);

  // Use channel code instead of user's invite code
  const shareCode = inviteInfo?.channel_code;

  // Generate invite link using channel code
  const inviteLink = shareCode
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/register?invite=${shareCode}`
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
    if (navigator.share && shareCode) {
      try {
        await navigator.share({
          title: `${shortName} 邀请注册`,
          text: `使用邀请码 ${shareCode} 注册 ${shortName}`,
          url: inviteLink,
        });
      } catch {
        // User cancelled or share failed
      }
    }
  };

  // No channel - show message
  const hasChannel = !!inviteInfo?.channel_id;

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
      ) : !hasChannel ? (
        // No channel - user cannot share invite
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="py-12 text-center">
            <Building2 className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {t("invite.noChannel")}
            </h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              {t("invite.noChannelDescription")}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Invite Code Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Gift className="w-5 h-5" />
                {t("invite.channelCode")}
              </CardTitle>
              <CardDescription>{t("invite.channelCodeDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Invite Code Display */}
              <div className="p-6 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
                <p className="text-sm text-muted-foreground mb-2">
                  {t("invite.channelCode")}
                </p>
                <div className="flex items-center justify-between">
                  <p className="text-3xl font-mono font-bold tracking-wider">
                    {shareCode || "-"}
                  </p>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleCopy("code", shareCode || "")}
                    disabled={!shareCode}
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
              {shareCode && (
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
                  disabled={!shareCode}
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  {t("invite.share")}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                {t("invite.howItWorks")}
              </CardTitle>
              <CardDescription>{t("invite.howItWorksDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* How it works */}
              <div className="space-y-3">
                <ul className="text-sm text-muted-foreground space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">1.</span>
                    {t("invite.step1")}
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">2.</span>
                    {t("invite.step2")}
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">3.</span>
                    {t("invite.step3")}
                  </li>
                </ul>
              </div>

              {/* Note */}
              <div className="p-4 rounded-lg bg-muted/30 text-sm text-muted-foreground">
                {t("invite.note")}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
