'use client';

import Link from 'next/link';
import { ArrowLeft, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface BadgeItem {
  label: string;
  className?: string;
}

interface MoreMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'default' | 'destructive';
  separatorBefore?: boolean;
  disabled?: boolean;
}

interface DetailPageHeaderProps {
  /** URL to navigate back to */
  backHref: string;
  /** Entity icon */
  icon: React.ReactNode;
  /** Page title */
  title: string;
  /** Description text */
  description?: string;
  /** Badge items */
  badges?: BadgeItem[];
  /** Primary action buttons (rendered on the right) */
  primaryActions?: React.ReactNode;
  /** More menu items (renders dropdown menu) */
  moreMenuItems?: MoreMenuItem[];
}

/**
 * Unified detail page header component
 *
 * Features:
 * - Back button with navigation
 * - Icon + title + badges
 * - Description text
 * - Primary action buttons
 * - Optional "more" dropdown menu
 *
 * @example
 * ```tsx
 * <DetailPageHeader
 *   backHref="/strategies"
 *   icon={<Bot className="w-6 h-6 text-primary" />}
 *   title="My Strategy"
 *   description="Strategy description"
 *   badges={[
 *     { label: "AI", className: "border-rose-500/30 text-rose-500" },
 *     { label: "Private", className: "border-muted-foreground/30 text-muted-foreground" },
 *   ]}
 *   primaryActions={
 *     <>
 *       <Button>Edit</Button>
 *       <Button>Create Agent</Button>
 *     </>
 *   }
 *   moreMenuItems={[
 *     { label: "Copy ID", icon: <Copy />, onClick: handleCopyId },
 *     { label: "Delete", icon: <Trash2 />, onClick: handleDelete, variant: "destructive", separatorBefore: true },
 *   ]}
 * />
 * ```
 */
export function DetailPageHeader({
  backHref,
  icon,
  title,
  description,
  badges,
  primaryActions,
  moreMenuItems,
}: DetailPageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="flex items-center gap-4">
        {/* Back Button */}
        <Link href={backHref}>
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <ArrowLeft className="w-5 h-5" />
          </Button>
        </Link>

        {/* Icon + Title + Badges */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-primary/10">{icon}</div>
          <div>
            <h1 className="text-2xl font-bold text-gradient">{title}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {badges?.map((badge, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className={cn('text-xs', badge.className)}
                >
                  {badge.label}
                </Badge>
              ))}
              {description && (
                <span className="text-sm text-muted-foreground line-clamp-1">
                  {description}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 ml-14 lg:ml-0">
        {primaryActions}

        {/* More Menu */}
        {moreMenuItems && moreMenuItems.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {moreMenuItems.map((item, index) => (
                <div key={index}>
                  {item.separatorBefore && index > 0 && (
                    <DropdownMenuSeparator />
                  )}
                  <DropdownMenuItem
                    variant={item.variant}
                    onClick={item.onClick}
                    disabled={item.disabled}
                  >
                    {item.icon && (
                      <span className="w-4 h-4 mr-2">{item.icon}</span>
                    )}
                    {item.label}
                  </DropdownMenuItem>
                </div>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
}
