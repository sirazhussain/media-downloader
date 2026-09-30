"use client";

import * as React from "react";
import { Check, Video, Volume2, Sparkles, Filter } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatFileSize } from "@/lib/utils";
import type { MediaFormat } from "@/types/media";

interface FormatSelectorProps {
  formats: MediaFormat[];
  selectedFormatId: string | null;
  onSelect: (formatId: string) => void;
  disabled?: boolean;
}

type TabType = "all" | "combined" | "audio" | "video_only";

export function FormatSelector({
  formats,
  selectedFormatId,
  onSelect,
  disabled = false,
}: FormatSelectorProps) {
  const [activeTab, setActiveTab] = React.useState<TabType>("combined");

  // Determine available categories
  const hasCombined = React.useMemo(() => formats.some((f) => f.has_video && f.has_audio), [formats]);
  const hasAudio = React.useMemo(() => formats.some((f) => !f.has_video && f.has_audio), [formats]);
  const hasVideoOnly = React.useMemo(() => formats.some((f) => f.has_video && !f.has_audio), [formats]);

  // Adjust default tab if no combined formats exist
  React.useEffect(() => {
    if (!hasCombined && hasAudio) {
      setActiveTab("audio");
    } else if (!hasCombined && hasVideoOnly) {
      setActiveTab("video_only");
    }
  }, [hasCombined, hasAudio, hasVideoOnly]);

  const filteredFormats = React.useMemo(() => {
    switch (activeTab) {
      case "combined":
        return formats.filter((f) => f.has_video && f.has_audio);
      case "audio":
        return formats.filter((f) => !f.has_video && f.has_audio);
      case "video_only":
        return formats.filter((f) => f.has_video && !f.has_audio);
      case "all":
      default:
        return formats;
    }
  }, [formats, activeTab]);

  // If filtered list is empty, fallback to showing all
  const displayFormats = filteredFormats.length > 0 ? filteredFormats : formats;

  if (formats.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        No downloadable formats were found for this media.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3.5">
      {/* Filter Tabs for quick selection */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-xs font-medium">
        {hasCombined && (
          <button
            type="button"
            onClick={() => setActiveTab("combined")}
            className={cn(
              "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 transition-all cursor-pointer",
              activeTab === "combined"
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Sparkles className="size-3.5" />
            Video + Audio (Best)
          </button>
        )}

        {hasAudio && (
          <button
            type="button"
            onClick={() => setActiveTab("audio")}
            className={cn(
              "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 transition-all cursor-pointer",
              activeTab === "audio"
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Volume2 className="size-3.5" />
            Audio Only
          </button>
        )}

        {hasVideoOnly && (
          <button
            type="button"
            onClick={() => setActiveTab("video_only")}
            className={cn(
              "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 transition-all cursor-pointer",
              activeTab === "video_only"
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Video className="size-3.5" />
            Video Only
          </button>
        )}

        <button
          type="button"
          onClick={() => setActiveTab("all")}
          className={cn(
            "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 transition-all cursor-pointer",
            activeTab === "all"
              ? "bg-primary text-primary-foreground font-semibold shadow-sm"
              : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <Filter className="size-3.5" />
          All ({formats.length})
        </button>
      </div>

      {/* Formats Grid */}
      <div
        role="radiogroup"
        aria-label="Available formats"
        className="grid grid-cols-1 gap-2.5 sm:grid-cols-2"
      >
        {displayFormats.map((format) => {
          const selected = format.format_id === selectedFormatId;
          const isCombined = format.has_video && format.has_audio;
          const isAudioOnly = !format.has_video && format.has_audio;

          return (
            <button
              key={format.format_id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onSelect(format.format_id)}
              className={cn(
                "group relative flex items-center justify-between gap-3 rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                "hover:border-primary/50 hover:bg-accent/40 active:scale-[0.99]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "disabled:cursor-not-allowed disabled:opacity-50",
                selected
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-sm"
                  : "border-border/80 bg-card"
              )}
            >
              <div className="flex min-w-0 flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-foreground">
                    {format.quality || "Default"}
                  </span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {format.ext}
                  </span>
                  {isCombined && (
                    <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                      Audio Included
                    </span>
                  )}
                  {isAudioOnly && (
                    <span className="rounded bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-medium text-indigo-600 dark:text-indigo-400">
                      Audio
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  {format.width && format.height && (
                    <span>
                      {format.width}×{format.height}
                    </span>
                  )}
                  {format.filesize != null && (
                    <span className="font-medium text-foreground/80">
                      {formatFileSize(format.filesize)}
                    </span>
                  )}
                </div>
              </div>

              {/* Radio Indicator */}
              <div
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full border transition-all",
                  selected
                    ? "border-primary bg-primary text-primary-foreground shadow-sm"
                    : "border-muted-foreground/30 group-hover:border-primary/50"
                )}
                aria-hidden
              >
                {selected && <Check className="size-3 stroke-[2.5]" />}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function FormatSelectorSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <Skeleton className="h-8 w-28 rounded-lg" />
        <Skeleton className="h-8 w-24 rounded-lg" />
        <Skeleton className="h-8 w-20 rounded-lg" />
      </div>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
