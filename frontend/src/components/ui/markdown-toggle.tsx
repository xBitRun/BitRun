"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Eye, Code } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarkdownToggleProps {
  content: string;
  defaultMode?: "read" | "source";
  className?: string;
}

export function MarkdownToggle({
  content,
  defaultMode = "read",
  className,
}: MarkdownToggleProps) {
  const [mode, setMode] = useState<"read" | "source">(defaultMode);

  if (!content) return null;

  return (
    <div className={cn("relative", className)}>
      {/* Toggle buttons */}
      <div className="flex justify-end mb-2">
        <div className="inline-flex rounded-md border border-border/50 bg-muted/30 p-0.5">
          <button
            type="button"
            onClick={() => setMode("read")}
            className={cn(
              "inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs transition-colors",
              mode === "read"
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Eye className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={() => setMode("source")}
            className={cn(
              "inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs transition-colors",
              mode === "source"
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Code className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Content */}
      {mode === "read" ? (
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : (
        <pre className="text-sm font-mono whitespace-pre-wrap text-muted-foreground p-4 rounded-lg bg-muted/20 border border-border/30 overflow-auto">
          {content}
        </pre>
      )}
    </div>
  );
}
