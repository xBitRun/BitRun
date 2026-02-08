"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Code, Eye } from "lucide-react";

interface MonacoMarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: number;
  maxHeight?: number;
  className?: string;
  readOnly?: boolean;
}

export function MonacoMarkdownEditor({
  value,
  onChange,
  placeholder,
  minHeight = 400,
  maxHeight,
  className,
  readOnly = false,
}: MonacoMarkdownEditorProps) {
  const t = useTranslations("editor");
  const [mode, setMode] = useState<"source" | "preview">("source");

  return (
    <div
      className={cn(
        "relative rounded-lg border border-input overflow-hidden bg-background",
        className
      )}
      style={{
        minHeight: `${minHeight}px`,
        maxHeight: maxHeight ? `${maxHeight}px` : undefined,
      }}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-end gap-1 px-3 py-2 border-b border-input bg-muted/30">
        <button
          type="button"
          onClick={() => setMode("source")}
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
            mode === "source"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          )}
        >
          <Code className="w-3.5 h-3.5" />
          {t("source")}
        </button>
        <button
          type="button"
          onClick={() => setMode("preview")}
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
            mode === "preview"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          )}
        >
          <Eye className="w-3.5 h-3.5" />
          {t("preview")}
        </button>
      </div>

      {/* Content Area */}
      <div
        className="relative"
        style={{
          minHeight: `${minHeight - 45}px`,
          maxHeight: maxHeight ? `${maxHeight - 45}px` : undefined,
        }}
      >
        {mode === "source" ? (
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            readOnly={readOnly}
            className={cn(
              "w-full h-full resize-none bg-transparent p-4 text-sm",
              "font-mono leading-relaxed",
              "placeholder:text-muted-foreground/50",
              "focus:outline-none",
              "scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
            )}
            style={{
              minHeight: `${minHeight - 45}px`,
              maxHeight: maxHeight ? `${maxHeight - 45}px` : undefined,
            }}
          />
        ) : (
          <div
            className={cn(
              "prose prose-sm dark:prose-invert max-w-none p-4 overflow-auto",
              "prose-headings:font-semibold prose-headings:tracking-tight",
              "prose-p:leading-relaxed prose-p:text-foreground/90",
              "prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono",
              "prose-pre:bg-muted prose-pre:border prose-pre:border-input",
              "prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground",
              "prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5",
              "prose-a:text-primary prose-a:no-underline hover:prose-a:underline"
            )}
            style={{
              minHeight: `${minHeight - 45}px`,
              maxHeight: maxHeight ? `${maxHeight - 45}px` : undefined,
            }}
          >
            {value ? (
              <ReactMarkdown>{value}</ReactMarkdown>
            ) : (
              <p className="text-muted-foreground/50 italic">
                {placeholder || t("empty")}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
