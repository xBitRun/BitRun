"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  User,
  Bell,
  Key,
  Shield,
  Save,
  Loader2,
  Check,
  AlertCircle,
  Mail,
  MessageSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { authApi } from "@/lib/api";

// Telegram icon component
function TelegramIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
    </svg>
  );
}

// Discord icon component
function DiscordIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/>
    </svg>
  );
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const { user, checkAuth } = useAuthStore();

  // Profile state
  const [profileForm, setProfileForm] = useState({
    name: user?.name || "",
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);

  // Notification state
  const [notifications, setNotifications] = useState({
    emailEnabled: false,
    telegramEnabled: false,
    discordEnabled: false,
    decisionAlerts: true,
    tradeAlerts: true,
    riskAlerts: true,
  });

  // Handle profile save
  const handleSaveProfile = async () => {
    setProfileSaving(true);
    try {
      await authApi.updateProfile({ name: profileForm.name });
      await checkAuth();
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (error) {
      console.error("Failed to update profile:", error);
    } finally {
      setProfileSaving(false);
    }
  };

  // Handle password change
  const handleChangePassword = async () => {
    setPasswordError("");

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError(t("password.mismatch"));
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      setPasswordError(t("password.tooShort"));
      return;
    }

    setPasswordSaving(true);
    try {
      await authApi.changePassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      });
      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setPasswordSaved(true);
      setTimeout(() => setPasswordSaved(false), 3000);
    } catch (error: unknown) {
      const err = error as { message?: string };
      setPasswordError(err.message || t("password.failed"));
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <User className="w-4 h-4" />
            {t("tabs.profile")}
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="w-4 h-4" />
            {t("tabs.notifications")}
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            {t("tabs.security")}
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="space-y-6">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                {t("profile.title")}
              </CardTitle>
              <CardDescription>{t("profile.description")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">{t("profile.email")}</Label>
                <Input
                  id="email"
                  type="email"
                  value={user?.email || ""}
                  disabled
                  className="bg-muted/50"
                />
                <p className="text-xs text-muted-foreground">
                  {t("profile.emailHint")}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">{t("profile.name")}</Label>
                <Input
                  id="name"
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  placeholder={t("profile.namePlaceholder")}
                />
              </div>

              <Button
                onClick={handleSaveProfile}
                disabled={profileSaving}
                className="w-full sm:w-auto"
              >
                {profileSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : profileSaved ? (
                  <Check className="w-4 h-4 mr-2" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                {profileSaved ? t("saved") : t("save")}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          {/* Channel Configuration */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                {t("notifications.channels")}
              </CardTitle>
              <CardDescription>{t("notifications.channelsDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Telegram */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[#0088cc]/10">
                    <TelegramIcon className="w-5 h-5 text-[#0088cc]" />
                  </div>
                  <div>
                    <p className="font-medium">Telegram</p>
                    <p className="text-sm text-muted-foreground">
                      {t("notifications.telegramDescription")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-muted-foreground">
                    {t("notifications.serverConfig")}
                  </Badge>
                </div>
              </div>

              {/* Discord */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[#5865F2]/10">
                    <DiscordIcon className="w-5 h-5 text-[#5865F2]" />
                  </div>
                  <div>
                    <p className="font-medium">Discord</p>
                    <p className="text-sm text-muted-foreground">
                      {t("notifications.discordDescription")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-muted-foreground">
                    {t("notifications.serverConfig")}
                  </Badge>
                </div>
              </div>

              {/* Email */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Mail className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Email</p>
                    <p className="text-sm text-muted-foreground">
                      {t("notifications.emailDescription")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-muted-foreground">
                    {t("notifications.serverConfig")}
                  </Badge>
                </div>
              </div>

              <p className="text-sm text-muted-foreground">
                {t("notifications.configHint")}
              </p>
            </CardContent>
          </Card>

          {/* Alert Preferences */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                {t("notifications.preferences")}
              </CardTitle>
              <CardDescription>{t("notifications.preferencesDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{t("notifications.decisionAlerts")}</p>
                  <p className="text-sm text-muted-foreground">
                    {t("notifications.decisionAlertsDescription")}
                  </p>
                </div>
                <Switch
                  checked={notifications.decisionAlerts}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, decisionAlerts: checked })
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{t("notifications.tradeAlerts")}</p>
                  <p className="text-sm text-muted-foreground">
                    {t("notifications.tradeAlertsDescription")}
                  </p>
                </div>
                <Switch
                  checked={notifications.tradeAlerts}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, tradeAlerts: checked })
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{t("notifications.riskAlerts")}</p>
                  <p className="text-sm text-muted-foreground">
                    {t("notifications.riskAlertsDescription")}
                  </p>
                </div>
                <Switch
                  checked={notifications.riskAlerts}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, riskAlerts: checked })
                  }
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          {/* Change Password */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="w-5 h-5" />
                {t("security.changePassword")}
              </CardTitle>
              <CardDescription>{t("security.changePasswordDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {passwordError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <p className="text-sm">{passwordError}</p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="currentPassword">{t("security.currentPassword")}</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(e) =>
                    setPasswordForm({ ...passwordForm, currentPassword: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">{t("security.newPassword")}</Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(e) =>
                    setPasswordForm({ ...passwordForm, newPassword: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">{t("security.confirmPassword")}</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={passwordForm.confirmPassword}
                  onChange={(e) =>
                    setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })
                  }
                />
              </div>

              <Button
                onClick={handleChangePassword}
                disabled={passwordSaving || !passwordForm.currentPassword || !passwordForm.newPassword}
                className="w-full sm:w-auto"
              >
                {passwordSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : passwordSaved ? (
                  <Check className="w-4 h-4 mr-2" />
                ) : (
                  <Key className="w-4 h-4 mr-2" />
                )}
                {passwordSaved ? t("saved") : t("security.updatePassword")}
              </Button>
            </CardContent>
          </Card>

          {/* API Access Info */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                {t("security.apiAccess")}
              </CardTitle>
              <CardDescription>{t("security.apiAccessDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-muted/30">
                  <p className="text-sm text-muted-foreground">
                    {t("security.apiNote")}
                  </p>
                </div>
                <p className="text-sm">
                  {t("security.exchangeKeysNote")}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
