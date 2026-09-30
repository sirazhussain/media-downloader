"use client";

import * as React from "react";
import { Check, Video, Volume2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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

function StreamBadges({ format }: { format: MediaFormat }) {
  if (format.has_video && format.has_audio) {
    return (
      <Badge variant="secondary" className="gap-1">
        <Video className="size-3" aria-hidden />
        Video + Audio
      </Badge>
    );
  }
  if (format.has_video) {
    return (
      <Badge variant="outline" className="gap-1">
        <Video className="size-3" aria-hidden />
        Video only
      </Badge>
    );
  }
  if (format.has_audio) {
    return (
      <Badge variant="outline" className="gap-1">
        <Volume2 className="size-3" aria-hidden />
        Audio only
      </Badge>
    );
  }
  return null;
}

/**
 * Renders only the formats present in the API response — quality options
 * are never hard-coded; whatever yt-dlp exposed is what the user sees.
 */
export function FormatSelector({
  formats,
  selectedFormatId,
  onSelect,
  disabled = false,
}: FormatSelectorProps) {
  if (formats.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No downloadable formats were found for this media.
      </p>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Available formats"
      className="grid grid-cols-1 gap-2.5 sm:grid-cols-2"
    >
      {formats.map((format) => {
        const selected = format.format_id === selectedFormatId;
        return (
          <button
            key={format.format_id}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onSelect(format.format_id)}
            className={cn(
              "flex items-center justify-between gap-3 rounded-xl border bg-card p-4 text-left shadow-sm transition-colors",
              "hover:border-primary/40 hover:bg-accent/50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "disabled:cursor-not-allowed disabled:opacity-50",
              selected && "border-primary ring-1 ring-primary"
            )}
          >
            <div className="flex min-w-0 flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">{format.quality}</span>
                <span className="text-xs uppercase text-muted-foreground">
                  {format.ext}
                </span>
                {format.width && format.height && (
                  <span className="text-xs text-muted-foreground">
                    {format.width}×{format.height}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <StreamBadges format={format} />
                {format.filesize != null && (
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(format.filesize)}
                  </span>
                )}
              </div>
            </div>
            <span
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full border",
                selected ? "border-primary bg-primary text-primary-foreground" : "border-input"
              )}
              aria-hidden
            >
              {selected && <Check className="size-3" />}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function FormatSelectorSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-20" />
      ))}
    </div>
  );
}
