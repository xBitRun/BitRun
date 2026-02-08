"use client";

import { Lightbulb, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TipItem {
  /** Tip title */
  title: string;
  /** Tip description */
  description: string;
}

interface TipsToggleProps {
  /** Whether tips are shown */
  show: boolean;
  /** Callback to toggle tips visibility */
  onToggle: () => void;
  /** Toggle button label */
  label?: string;
  /** Array of tip items to display */
  tips: TipItem[];
  /** Number of columns for tips grid (default: 3) */
  columns?: 1 | 2 | 3;
}

/**
 * Inline tips toggle component for form cards
 *
 * Features:
 * - Toggle button with icon
 * - Grid layout for tip items
 * - Consistent styling
 *
 * @example
 * ```tsx
 * const [showTips, setShowTips] = useState(false);
 *
 * <TipsToggle
 *   show={showTips}
 *   onToggle={() => setShowTips(!showTips)}
 *   label="Tips"
 *   tips={[
 *     { title: "Tip 1", description: "Description 1" },
 *     { title: "Tip 2", description: "Description 2" },
 *   ]}
 * />
 * ```
 */
export function TipsToggle({
  show,
  onToggle,
  label = "Tips",
  tips,
  columns = 3,
}: TipsToggleProps) {
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        className="text-muted-foreground"
      >
        <Lightbulb className="w-4 h-4 mr-1" />
        {label}
        {show ? (
          <ChevronUp className="w-4 h-4 ml-1" />
        ) : (
          <ChevronDown className="w-4 h-4 ml-1" />
        )}
      </Button>

      {show && (
        <TipsContent tips={tips} columns={columns} />
      )}
    </>
  );
}

interface TipsContentProps {
  tips: TipItem[];
  columns?: 1 | 2 | 3;
}

/**
 * Standalone tips content component (without toggle button)
 * Use this when you need to display tips in a custom layout
 */
export function TipsContent({ tips, columns = 3 }: TipsContentProps) {
  const gridCols = {
    1: "grid-cols-1",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-3",
  };

  return (
    <div className="mt-4 p-4 rounded-lg bg-muted/50 text-sm space-y-3">
      <div className={`grid ${gridCols[columns]} gap-4`}>
        {tips.map((tip, index) => (
          <div key={index}>
            <p className="font-medium mb-1">{tip.title}</p>
            <p className="text-muted-foreground text-xs">{tip.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
