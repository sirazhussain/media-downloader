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

type TabType = "video" | "audio";

export function FormatSelector({
  formats,
  selectedFormatId,
  onSelect,
  disabled = false,
}: FormatSelectorProps) {
  const hasVideo = React.useMemo(() => formats.some((f) => f.has_video), [formats]);
  const hasAudio = React.useMemo(() => formats.some((f) => !f.has_video), [formats]);

  const [activeTab, setActiveTab] = React.useState<TabType>(hasVideo ? "video" : "audio");

  React.useEffect(() => {
    if (!hasVideo && hasAudio) {
      setActiveTab("audio");
    } else if (hasVideo) {
      setActiveTab("video");
    }
  }, [hasVideo, hasAudio]);

  const videoFormats = React.useMemo(() => formats.filter((f) => f.has_video), [formats]);
  const audioFormats = React.useMemo(() => formats.filter((f) => !f.has_video), [formats]);

  const displayFormats = React.useMemo(() => {
    if (activeTab === "audio") {
      return audioFormats.length > 0 ? audioFormats : formats;
    }
    return videoFormats.length > 0 ? videoFormats : formats;
  }, [formats, activeTab, audioFormats, videoFormats]);

  if (formats.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
        No downloadable formats were found for this media.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3.5">
      {/* Category Tabs: Video or Audio */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-xs font-medium">
        {hasVideo && (
          <button
            type="button"
            onClick={() => setActiveTab("video")}
            className={cn(
              "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 py-1.5 transition-all cursor-pointer",
              activeTab === "video"
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Video className="size-3.5" />
            Video (MP4) {videoFormats.length > 0 && `(${videoFormats.length})`}
          </button>
        )}

        {hasAudio && (
          <button
            type="button"
            onClick={() => setActiveTab("audio")}
            className={cn(
              "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 py-1.5 transition-all cursor-pointer",
              activeTab === "audio"
                ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Volume2 className="size-3.5" />
            Audio Only {audioFormats.length > 0 && `(${audioFormats.length})`}
          </button>
        )}
      </div>

      {/* Formats Grid */}
      <div
        role="radiogroup"
        aria-label="Available formats"
        className="grid grid-cols-1 gap-2.5 sm:grid-cols-2"
      >
        {displayFormats.map((format) => {
          const selected = format.format_id === selectedFormatId;
          const isVideo = format.has_video;
          const isHD = (format.height || 0) >= 720;

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
                    {format.quality || "Standard"}
                  </span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {format.ext}
                  </span>
                  {isVideo && isHD && (
                    <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                      HD
                    </span>
                  )}
                  {isVideo && (
                    <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                      Audio Included
                    </span>
                  )}
                  {!isVideo && (
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
