"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface CollapsibleCardProps {
  /** Card title */
  title: string;
  /** Card description/subtitle */
  description?: string;
  /** Icon to display next to title */
  icon?: React.ReactNode;
  /** Whether the card is expanded */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Card content */
  children: React.ReactNode;
  /** Additional class names for the card */
  className?: string;
}

/**
 * Collapsible card component for advanced/optional settings
 *
 * Features:
 * - Clickable header to toggle content
 * - Animated chevron indicator
 * - Hover effect on header
 * - Consistent styling with other form cards
 *
 * @example
 * ```tsx
 * const [showAdvanced, setShowAdvanced] = useState(false);
 *
 * <CollapsibleCard
 *   open={showAdvanced}
 *   onOpenChange={setShowAdvanced}
 *   title="Advanced Settings"
 *   description="Configure advanced options"
 *   icon={<Settings className="w-4 h-4 text-primary" />}
 * >
 *   <div>Advanced content here</div>
 * </CollapsibleCard>
 * ```
 */
export function CollapsibleCard({
  title,
  description,
  icon,
  open,
  onOpenChange,
  children,
  className,
}: CollapsibleCardProps) {
  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <Card className={className}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                {icon}
                {title}
              </CardTitle>
              {open ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
            {description && (
              <CardDescription className="text-left">
                {description}
              </CardDescription>
            )}
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0">
            {children}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
