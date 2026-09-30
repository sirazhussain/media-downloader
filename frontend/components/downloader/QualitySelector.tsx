"use client";

import * as React from "react";
import { FormatSelector } from "./FormatSelector";
import type { MediaFormat } from "@/types/media";

interface QualitySelectorProps {
  formats: MediaFormat[];
  selectedFormatId: string | null;
  onSelect: (formatId: string) => void;
  disabled?: boolean;
}

export function QualitySelector({
  formats,
  selectedFormatId,
  onSelect,
  disabled = false,
}: QualitySelectorProps) {
  return (
    <FormatSelector
      formats={formats}
      selectedFormatId={selectedFormatId}
      onSelect={onSelect}
      disabled={disabled}
    />
  );
}
