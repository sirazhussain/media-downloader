"use client";

import * as React from "react";
import { FormatSelector } from "./FormatSelector";
import { Separator } from "@/components/ui/separator";
import type { MediaFormat } from "@/types/media";

interface QualitySelectorProps {
  formats: MediaFormat[];
  selectedFormatId: string | null;
  onSelect: (formatId: string) => void;
  disabled?: boolean;
}

function groupByQuality(formats: MediaFormat[]): Map<string, MediaFormat[]> {
  const groups = new Map<string, MediaFormat[]>();
  for (const format of formats) {
    const key = format.quality || "Unknown";
    const list = groups.get(key);
    if (list) list.push(format);
    else groups.set(key, [format]);
  }
  return groups;
}

/** Sorts quality groups numerically (1080p > 720p > …) when parseable. */
function qualityRank(label: string): number {
  const match = /(\d+)\s*p/i.exec(label);
  if (match) return parseInt(match[1], 10);
  if (/audio/i.test(label)) return -1;
  return 0;
}

/**
 * Groups available formats by their quality label (e.g. all 720p variants
 * together), then renders each group with the FormatSelector. Qualities
 * come entirely from the API response — nothing is hard-coded.
 */
export function QualitySelector({
  formats,
  selectedFormatId,
  onSelect,
  disabled = false,
}: QualitySelectorProps) {
  const groups = React.useMemo(() => {
    const grouped = groupByQuality(formats);
    return [...grouped.entries()].sort(
      ([a], [b]) => qualityRank(b) - qualityRank(a)
    );
  }, [formats]);

  if (groups.length <= 1) {
    return (
      <FormatSelector
        formats={formats}
        selectedFormatId={selectedFormatId}
        onSelect={onSelect}
        disabled={disabled}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {groups.map(([quality, groupFormats], index) => (
        <div key={quality} className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-foreground">{quality}</h3>
            <Separator className="flex-1" />
          </div>
          <FormatSelector
            formats={groupFormats}
            selectedFormatId={selectedFormatId}
            onSelect={onSelect}
            disabled={disabled}
          />
          {index < groups.length - 1 && <span className="sr-only">,</span>}
        </div>
      ))}
    </div>
  );
}
