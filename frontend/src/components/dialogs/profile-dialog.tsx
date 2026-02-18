"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { User, Shield, Loader2, Eye, EyeOff, Check, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useAuthStore } from "@/stores/auth-store";
import { authApi } from "@/lib/api";

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const t = useTranslations("profile");
  const { user, checkAuth } = useAuthStore();
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Password change state
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwords, setPasswords] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  const [profile, setProfile] = useState({
    name: user?.name || "",
    email: user?.email || "",
  });

  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);

  // Update profile state when user changes
  useEffect(() => {
    if (user) {
      setProfile({
        name: user.name || "",
        email: user.email || "",
      });
    }
  }, [user]);

  // Reset states when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setSaveError(null);
      setSaveSuccess(false);
      setShowPasswordChange(false);
      setPasswordError(null);
      setPasswordSuccess(false);
      setPasswords({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    }
  }, [open]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      // Only update if name changed
      if (profile.name !== user?.name) {
        await authApi.updateProfile({ name: profile.name });
        // Refresh user info in auth store
        await checkAuth();
        setSaveSuccess(true);
        setTimeout(() => {
          onOpenChange(false);
        }, 1000);
      } else {
        onOpenChange(false);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.failedToUpdateProfile");
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    // Validate passwords
    if (passwords.newPassword !== passwords.confirmPassword) {
      setPasswordError(t("passwordMismatch"));
      return;
    }

    if (passwords.newPassword.length < 8) {
      setPasswordError(t("passwordTooShort"));
      return;
    }

    setIsChangingPassword(true);
    setPasswordError(null);
    setPasswordSuccess(false);

    try {
      await authApi.changePassword({
        current_password: passwords.currentPassword,
        new_password: passwords.newPassword,
      });
      setPasswordSuccess(true);
      setPasswords({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
      setTimeout(() => {
        setShowPasswordChange(false);
        setPasswordSuccess(false);
      }, 2000);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.failedToChangePassword");
      setPasswordError(message);
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleCancelPasswordChange = () => {
    setShowPasswordChange(false);
    setPasswordError(null);
    setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-primary" />
            {t("title")}
          </DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Profile Information */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <div className="space-y-2">
                <Label htmlFor="profile-name">{t("name")}</Label>
                <Input
                  id="profile-name"
                  value={profile.name}
                  onChange={(e) =>
                    setProfile({ ...profile, name: e.target.value })
                  }
                  placeholder={t("namePlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="profile-email">{t("email")}</Label>
                <Input
                  id="profile-email"
                  type="email"
                  value={profile.email}
                  disabled
                  className="bg-muted/50"
                />
                <p className="text-xs text-muted-foreground">
                  {t("emailReadonly")}
                </p>
              </div>
            </div>

            {/* Save error/success messages */}
            {saveError && (
              <div className="p-3 text-sm text-red-400 bg-red-500/10 rounded-lg border border-red-500/20">
                {saveError}
              </div>
            )}
            {saveSuccess && (
              <div className="p-3 text-sm text-green-400 bg-green-500/10 rounded-lg border border-green-500/20 flex items-center gap-2">
                <Check className="w-4 h-4" />
                {t("profileUpdated")}
              </div>
            )}
          </div>

          {/* Security Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Shield className="w-4 h-4 text-primary" />
              {t("security")}
            </div>

            {!showPasswordChange ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPasswordChange(true)}
              >
                {t("changePassword")}
              </Button>
            ) : (
              <div className="space-y-4 p-4 rounded-lg bg-muted/30 border border-border/30">
                <div className="space-y-2">
                  <Label htmlFor="current-password">
                    {t("currentPassword")}
                  </Label>
                  <div className="relative">
                    <Input
                      id="current-password"
                      type={showCurrentPassword ? "text" : "password"}
                      value={passwords.currentPassword}
                      onChange={(e) =>
                        setPasswords({
                          ...passwords,
                          currentPassword: e.target.value,
                        })
                      }
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setShowCurrentPassword(!showCurrentPassword)
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showCurrentPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-password">{t("newPassword")}</Label>
                  <div className="relative">
                    <Input
                      id="new-password"
                      type={showNewPassword ? "text" : "password"}
                      value={passwords.newPassword}
                      onChange={(e) =>
                        setPasswords({
                          ...passwords,
                          newPassword: e.target.value,
                        })
                      }
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showNewPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t("passwordRequirements")}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm-password">
                    {t("confirmPassword")}
                  </Label>
                  <Input
                    id="confirm-password"
                    type={showNewPassword ? "text" : "password"}
                    value={passwords.confirmPassword}
                    onChange={(e) =>
                      setPasswords({
                        ...passwords,
                        confirmPassword: e.target.value,
                      })
                    }
                    placeholder="••••••••"
                  />
                </div>

                {passwordError && (
                  <div className="p-3 text-sm text-red-400 bg-red-500/10 rounded-lg border border-red-500/20">
                    {passwordError}
                  </div>
                )}

                {passwordSuccess && (
                  <div className="p-3 text-sm text-green-400 bg-green-500/10 rounded-lg border border-green-500/20 flex items-center gap-2">
                    <Check className="w-4 h-4" />
                    {t("passwordChanged")}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancelPasswordChange}
                    disabled={isChangingPassword}
                  >
                    <X className="w-4 h-4 mr-1" />
                    {t("cancel")}
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleChangePassword}
                    disabled={
                      isChangingPassword ||
                      !passwords.currentPassword ||
                      !passwords.newPassword ||
                      !passwords.confirmPassword
                    }
                  >
                    {isChangingPassword ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4 mr-1" />
                    )}
                    {t("updatePassword")}
                  </Button>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/30">
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{t("twoFactor")}</p>
                <p className="text-xs text-muted-foreground">
                  {t("twoFactorDescription")}
                </p>
              </div>
              <Switch
                checked={twoFactorEnabled}
                onCheckedChange={setTwoFactorEnabled}
                disabled
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {t("twoFactorComingSoon")}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("cancel")}
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : null}
            {t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
