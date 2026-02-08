"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import Image from "next/image";
import { LogOut, Menu, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LanguageSwitcher } from "./language-switcher";
import { useAuthStore } from "@/stores/auth-store";

interface HeaderProps {
  /** "dashboard" shows user menu; "landing" shows login button + logo */
  variant?: "dashboard" | "landing";
  onMenuClick?: () => void;
}

export function Header({ variant = "dashboard", onMenuClick }: HeaderProps) {
  const t = useTranslations("header");
  const tLanding = useTranslations("landing");
  const { user, logout, isLoading } = useAuthStore();

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.name) {
      return user.name.charAt(0).toUpperCase();
    }
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return "U";
  };

  const handleLogout = async () => {
    await logout();
    // Auth guard will handle redirect to login
  };

  const isLanding = variant === "landing";

  return (
    <header
      className={
        isLanding
          ? "fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8 bg-transparent"
          : "flex items-center justify-between h-16 px-4 md:px-6 border-b border-border bg-background/50 backdrop-blur-sm"
      }
    >
      {/* Left side */}
      <div className="flex items-center gap-3">
        {isLanding ? (
          /* Landing: BITRUN logo */
          <Link href="/" className="flex items-center">
            <Image
              src="/logo.png"
              alt="BITRUN"
              width={200}
              height={64}
              className="h-14 w-auto"
              priority
            />
          </Link>
        ) : (
          /* Dashboard: Mobile menu button */
          onMenuClick && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onMenuClick}
              className="md:hidden"
            >
              <Menu className="w-5 h-5" />
            </Button>
          )
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 md:gap-4">
        {/* Status indicator - dashboard only, hidden on mobile */}
        {!isLanding && (
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <span className="text-xs text-muted-foreground">
              {t("systemOnline")}
            </span>
          </div>
        )}

        {/* Language Switcher */}
        <LanguageSwitcher />

        {isLanding ? (
          /* Landing: Login button - pill style matching ReactBits */
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 rounded-full border border-foreground/10 bg-foreground/5 px-4 py-1.5 text-sm font-medium text-foreground/80 transition-all hover:bg-foreground/10 hover:text-foreground"
          >
            {tLanding("nav.login")}
          </Link>
        ) : (
          /* Dashboard: User menu */
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-full hover:bg-muted/50 transition-colors p-1 pr-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
                <Avatar className="w-8 h-8">
                  <AvatarFallback className="bg-primary/20 text-primary text-sm font-medium">
                    {getUserInitials()}
                  </AvatarFallback>
                </Avatar>
                {user?.name && (
                  <span className="text-sm font-medium hidden md:block">
                    {user.name}
                  </span>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium">{user?.name || t("myAccount")}</p>
                  {user?.email && (
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings">
                  <Settings className="w-4 h-4 mr-2" />
                  {t("settings")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive cursor-pointer"
                onClick={handleLogout}
                disabled={isLoading}
              >
                <LogOut className="w-4 h-4 mr-2" />
                {t("logout")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  );
}
