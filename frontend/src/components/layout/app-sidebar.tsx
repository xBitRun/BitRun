"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import Image from "next/image";
import {
  LayoutDashboard,
  Bot,
  Sigma,
  Wallet,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
  Menu,
  Cpu,
  Trophy,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useState, useEffect } from "react";

const navItems = [
  {
    titleKey: "dashboard",
    href: "/overview",
    icon: LayoutDashboard,
  },
  {
    titleKey: "agents",
    href: "/agents",
    icon: Bot,
  },
  {
    titleKey: "strategies",
    href: "/strategies",
    icon: Sigma,
  },
  {
    titleKey: "accounts",
    href: "/accounts",
    icon: Wallet,
  },
  {
    titleKey: "competition",
    href: "/competition",
    icon: Trophy,
  },
  {
    titleKey: "models",
    href: "/models",
    icon: Cpu,
  },
  {
    titleKey: "backtest",
    href: "/backtest",
    icon: FlaskConical,
  },
] as const;

// Desktop Sidebar Component
function DesktopSidebar({ collapsed, setCollapsed }: { collapsed: boolean; setCollapsed: (v: boolean) => void }) {
  const t = useTranslations("nav");
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 py-2 border-b border-sidebar-border">
        <Link href="/overview" className="flex items-center h-full">
          <Image
            src="/logo.png"
            alt="BITRUN"
            width={160}
            height={48}
            className={cn("h-full w-auto", collapsed && "hidden")}
            priority
          />
          {collapsed && (
            <Image
              src="/logo.png"
              alt="BITRUN"
              width={48}
              height={48}
              className="h-full w-auto rounded-lg object-cover object-left"
            />
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/overview" && pathname.startsWith(item.href));

          const title = t(item.titleKey);

          const linkContent = (
            <Link
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
                collapsed && "justify-center px-2"
              )}
            >
              <item.icon
                className={cn("w-5 h-5 shrink-0", isActive && "text-primary")}
              />
              {!collapsed && (
                <span className="text-sm font-medium">{title}</span>
              )}
            </Link>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.href} delayDuration={0}>
                <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                <TooltipContent side="right" sideOffset={10}>
                  {title}
                </TooltipContent>
              </Tooltip>
            );
          }

          return <div key={item.href}>{linkContent}</div>;
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-sidebar-border">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "w-full justify-center text-muted-foreground hover:text-foreground",
            !collapsed && "justify-start"
          )}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4 mr-2" />
              <span className="text-xs">{t("collapse")}</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}

// Mobile Sidebar Component (Sheet)
function MobileSidebar({ open, setOpen }: { open: boolean; setOpen: (v: boolean) => void }) {
  const t = useTranslations("nav");
  const pathname = usePathname();

  // Close sidebar when route changes
  useEffect(() => {
    setOpen(false);
  }, [pathname, setOpen]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="left" className="w-64 p-0 bg-sidebar">
        {/* Logo */}
        <div className="flex items-center h-16 px-4 py-2 border-b border-sidebar-border">
          <Link href="/overview" className="flex items-center h-full">
            <Image
              src="/logo.png"
              alt="BITRUN"
              width={160}
              height={48}
              className="h-full w-auto"
            />
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/overview" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                )}
              >
                <item.icon
                  className={cn("w-5 h-5 shrink-0", isActive && "text-primary")}
                />
                <span className="text-sm font-medium">{t(item.titleKey)}</span>
              </Link>
            );
          })}
        </nav>
      </SheetContent>
    </Sheet>
  );
}

// Mobile Menu Button (to be used in Header)
export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onClick}
      className="md:hidden"
    >
      <Menu className="w-5 h-5" />
    </Button>
  );
}

interface AppSidebarProps {
  mobileOpen?: boolean;
  onMobileOpenChange?: (open: boolean) => void;
}

// Main AppSidebar Export
export function AppSidebar({ mobileOpen = false, onMobileOpenChange }: AppSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [internalMobileOpen, setInternalMobileOpen] = useState(false);
  
  // Support both controlled and uncontrolled mode
  const isOpen = onMobileOpenChange ? mobileOpen : internalMobileOpen;
  const setOpen = onMobileOpenChange ?? setInternalMobileOpen;

  return (
    <>
      {/* Desktop Sidebar */}
      <DesktopSidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      {/* Mobile Sidebar */}
      <MobileSidebar open={isOpen} setOpen={setOpen} />
    </>
  );
}
