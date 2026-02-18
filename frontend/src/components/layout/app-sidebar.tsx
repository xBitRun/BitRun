"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
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
  Store,
  TrendingUp,
  Building2,
  type LucideIcon,
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
import { BrandedLogo, LogoCompact } from "@/components/brand";
import { useAuthStore } from "@/stores/auth-store";

const navItems = [
  {
    titleKey: "dashboard",
    href: "/overview",
    icon: LayoutDashboard,
  },
  {
    titleKey: "marketplace",
    href: "/marketplace",
    icon: Store,
  },
  {
    titleKey: "strategies",
    href: "/strategies",
    icon: Sigma,
  },
  {
    titleKey: "agents",
    href: "/agents",
    icon: Bot,
  },
  {
    titleKey: "backtest",
    href: "/backtest",
    icon: FlaskConical,
  },
  {
    titleKey: "analytics",
    href: "/analytics",
    icon: TrendingUp,
  },
  {
    titleKey: "accounts",
    href: "/accounts",
    icon: Wallet,
  },
  {
    titleKey: "models",
    href: "/models",
    icon: Cpu,
  },
  {
    titleKey: "wallet",
    href: "/wallet",
    icon: Wallet,
  },
] as const;

// Platform admin section (only for platform_admin)
const adminNavItems = [
  {
    titleKey: "admin.channels",
    href: "/admin/channels",
    icon: Building2,
  },
  {
    titleKey: "admin.recharge",
    href: "/admin/recharge",
    icon: Wallet,
  },
  {
    titleKey: "admin.accounting",
    href: "/admin/accounting",
    icon: TrendingUp,
  },
] as const;

type NavItem = {
  titleKey: string;
  href: string;
  icon: LucideIcon;
};

// Helper to render nav items
function renderNavItems(
  items: readonly NavItem[],
  pathname: string,
  t: (key: string) => string,
  collapsed: boolean,
) {
  return items.map((item) => {
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
          collapsed && "justify-center px-2",
        )}
      >
        <item.icon
          className={cn("w-5 h-5 shrink-0", isActive && "text-primary")}
        />
        {!collapsed && <span className="text-sm font-medium">{title}</span>}
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
  });
}

// Desktop Sidebar Component
function DesktopSidebar({
  collapsed,
  setCollapsed,
}: {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);

  // Only platform_admin can see admin menu
  const showAdminNav = user?.role === "platform_admin";

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300",
        collapsed ? "w-16" : "w-64",
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 py-2 border-b border-sidebar-border">
        <Link href="/overview" className="flex items-center h-full">
          {collapsed ? (
            <LogoCompact
              width={48}
              height={48}
              className="h-full w-auto rounded-lg object-cover object-left"
            />
          ) : (
            <BrandedLogo width={160} height={48} priority />
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto scrollbar-thin">
        {/* Main Navigation */}
        {renderNavItems(navItems, pathname, t, collapsed)}

        {/* Platform Admin Section - only for platform_admin */}
        {showAdminNav && (
          <>
            {/* Divider */}
            {!collapsed && (
              <div className="my-3 border-t border-sidebar-border" />
            )}
            {renderNavItems(adminNavItems, pathname, t, collapsed)}
          </>
        )}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-sidebar-border">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "w-full justify-center text-muted-foreground hover:text-foreground",
            !collapsed && "justify-start",
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
function MobileSidebar({
  open,
  setOpen,
}: {
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);

  // Only platform_admin can see admin menu
  const showAdminNav = user?.role === "platform_admin";

  // Close sidebar when route changes
  useEffect(() => {
    setOpen(false);
  }, [pathname, setOpen]);

  // Helper to render mobile nav items
  const renderMobileNavItems = (items: readonly NavItem[]) =>
    items.map((item) => {
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
              : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
          )}
        >
          <item.icon
            className={cn("w-5 h-5 shrink-0", isActive && "text-primary")}
          />
          <span className="text-sm font-medium">{t(item.titleKey)}</span>
        </Link>
      );
    });

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="left" className="w-64 p-0 bg-sidebar">
        {/* Logo */}
        <div className="flex items-center h-16 px-4 py-2 border-b border-sidebar-border">
          <Link href="/overview" className="flex items-center h-full">
            <BrandedLogo width={160} height={48} />
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {/* Main Navigation */}
          {renderMobileNavItems(navItems)}

          {/* Platform Admin Section - only for platform_admin */}
          {showAdminNav && (
            <>
              {/* Divider */}
              <div className="my-3 border-t border-sidebar-border" />
              {renderMobileNavItems(adminNavItems)}
            </>
          )}
        </nav>
      </SheetContent>
    </Sheet>
  );
}

// Mobile Menu Button (to be used in Header)
export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" size="icon" onClick={onClick} className="md:hidden">
      <Menu className="w-5 h-5" />
    </Button>
  );
}

interface AppSidebarProps {
  mobileOpen?: boolean;
  onMobileOpenChange?: (open: boolean) => void;
}

// Main AppSidebar Export
export function AppSidebar({
  mobileOpen = false,
  onMobileOpenChange,
}: AppSidebarProps) {
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
