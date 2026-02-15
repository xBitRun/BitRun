"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useAuthStore, type AuthErrorInfo } from "@/stores/auth-store";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthPageSkeleton />}>
      <AuthPageContent />
    </Suspense>
  );
}

function AuthPageSkeleton() {
  return (
    <div className="w-full space-y-6">
      <div className="text-center space-y-2">
        <div className="h-8 w-48 mx-auto bg-white/5 animate-pulse rounded" />
        <div className="h-5 w-44 mx-auto bg-white/5 animate-pulse rounded" />
      </div>
      <div className="flex gap-3">
        <div className="flex-1 h-11 bg-white/5 animate-pulse rounded-lg" />
        <div className="flex-1 h-11 bg-white/5 animate-pulse rounded-lg" />
      </div>
      <div className="space-y-3">
        <div className="h-11 bg-white/5 animate-pulse rounded-lg" />
        <div className="h-11 bg-white/5 animate-pulse rounded-lg" />
        <div className="h-11 bg-white/5 animate-pulse rounded-lg" />
      </div>
    </div>
  );
}

function AuthPageContent() {
  const t = useTranslations("auth");
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/overview";
  const { login, register, isLoading, error, clearError } = useAuthStore();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [formError, setFormError] = useState<string | null>(null);

  /**
   * Convert structured error object to localized message.
   * Uses translation keys defined in auth.errors namespace.
   */
  const getErrorMessage = (err: AuthErrorInfo | null): string | null => {
    if (!err) return null;

    switch (err.code) {
      case "AUTH_INVALID_CREDENTIALS":
        // Show remaining attempts if available
        return err.remaining_attempts !== undefined
          ? t("errors.AUTH_INVALID_CREDENTIALS", {
              remaining: err.remaining_attempts,
            })
          : t("errors.AUTH_INVALID_CREDENTIALS_GENERIC");
      case "AUTH_ACCOUNT_LOCKED":
        return t("errors.AUTH_ACCOUNT_LOCKED", {
          minutes: err.remaining_minutes || 15,
        });
      case "AUTH_RATE_LIMITED":
        return t("errors.AUTH_RATE_LIMITED");
      case "AUTH_EMAIL_EXISTS":
        return t("errors.AUTH_EMAIL_EXISTS");
      case "SERVICE_UNAVAILABLE":
        return t("errors.SERVICE_UNAVAILABLE");
      case "REGISTER_FAILED":
        return t("errors.REGISTER_FAILED");
      case "LOGIN_FAILED":
      default:
        return t("errors.LOGIN_FAILED");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setFormError(null);
    clearError();
  };

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setFormError(null);
    clearError();
    setFormData({ name: "", email: "", password: "", confirmPassword: "" });
  };

  const validateForm = () => {
    if (!formData.email || !formData.password) {
      setFormError(t("errors.required"));
      return false;
    }
    if (!formData.email.includes("@")) {
      setFormError(t("errors.invalidEmail"));
      return false;
    }
    if (formData.password.length < 8) {
      setFormError(t("errors.passwordLength"));
      return false;
    }
    if (mode === "register") {
      if (!formData.name) {
        setFormError(t("errors.nameRequired"));
        return false;
      }
      if (formData.password !== formData.confirmPassword) {
        setFormError(t("errors.passwordMismatch"));
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    try {
      if (mode === "login") {
        await login({ email: formData.email, password: formData.password });
      } else {
        await register({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        });
      }
      router.push(callbackUrl);
    } catch {
      // Error handled by store
    }
  };

  // Form errors are already localized strings, API errors need conversion
  const displayError = formError || getErrorMessage(error);
  const isLogin = mode === "login";

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Title */}
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold text-white">
          {isLogin ? t("welcome") : t("createAccount")}
        </h1>
        <p className="text-sm text-white/50">
          {isLogin ? t("description") : t("registerDescription")}
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {displayError && (
          <div className="p-3 text-sm text-red-400 bg-red-500/10 rounded-lg border border-red-500/20">
            {displayError}
          </div>
        )}

        {/* Name field - only for register */}
        {!isLogin && (
          <Input
            name="name"
            type="text"
            placeholder={t("name")}
            value={formData.name}
            onChange={handleInputChange}
            disabled={isLoading}
            autoComplete="off"
            className="h-11 bg-white/3 border-white/10 text-white placeholder:text-white/40 rounded-lg focus:border-white/20 focus:ring-0"
          />
        )}

        <Input
          name="email"
          type="email"
          placeholder={t("email")}
          value={formData.email}
          onChange={handleInputChange}
          disabled={isLoading}
          autoComplete="off"
          className="h-11 bg-white/3 border-white/10 text-white placeholder:text-white/40 rounded-lg focus:border-white/20 focus:ring-0"
        />

        <div className="relative">
          <Input
            name="password"
            type={showPassword ? "text" : "password"}
            placeholder={t("password")}
            value={formData.password}
            onChange={handleInputChange}
            disabled={isLoading}
            autoComplete="off"
            className="h-11 bg-white/3 border-white/10 text-white placeholder:text-white/40 rounded-lg focus:border-white/20 focus:ring-0 pr-11"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="w-5 h-5" />
            ) : (
              <Eye className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Confirm Password - only for register */}
        {!isLogin && (
          <Input
            name="confirmPassword"
            type={showPassword ? "text" : "password"}
            placeholder={t("confirmPassword")}
            value={formData.confirmPassword}
            onChange={handleInputChange}
            disabled={isLoading}
            autoComplete="off"
            className="h-11 bg-white/3 border-white/10 text-white placeholder:text-white/40 rounded-lg focus:border-white/20 focus:ring-0"
          />
        )}

        <Button
          type="submit"
          disabled={isLoading}
          className="h-11 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white font-medium rounded-lg"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              {t("loading")}
            </>
          ) : isLogin ? (
            t("continue")
          ) : (
            t("registerButton")
          )}
        </Button>
      </form>

      {/* Switch Mode */}
      <p className="text-center text-sm text-white/50">
        {isLogin ? t("noAccount") : t("hasAccount")}{" "}
        <button
          type="button"
          onClick={switchMode}
          className="text-primary hover:text-primary/80 underline underline-offset-2"
        >
          {isLogin ? t("register") : t("login")}
        </button>
      </p>

      {/* Terms */}
      <p className="text-center text-xs text-white/30">
        {t("termsPrefix")}{" "}
        <Link href="/terms" className="underline hover:text-white/50">
          {t("termsOfService")}
        </Link>{" "}
        {t("and")}{" "}
        <Link href="/privacy" className="underline hover:text-white/50">
          {t("privacyPolicy")}
        </Link>
        .
      </p>
    </div>
  );
}
