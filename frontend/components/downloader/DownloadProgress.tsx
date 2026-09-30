"use client";

import { CheckCircle2, Loader2, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

export type DownloadPhase = "idle" | "preparing" | "downloading" | "done";

interface DownloadProgressProps {
  phase: DownloadPhase;
  onReset?: () => void;
}

const PHASE_COPY: Record<Exclude<DownloadPhase, "idle">, string> = {
  preparing: "Preparing download…",
  downloading: "Downloading to your device…",
  done: "Download started!",
};

export function DownloadProgress({ phase, onReset }: DownloadProgressProps) {
  if (phase === "idle") return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col gap-3 rounded-2xl border bg-card p-4 shadow-sm w-full"
    >
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex items-center gap-2.5">
          {phase === "done" ? (
            <CheckCircle2 className="size-5 text-emerald-500" aria-hidden />
          ) : (
            <Loader2 className="size-5 animate-spin text-primary" aria-hidden />
          )}
          <p className="text-sm font-medium">{PHASE_COPY[phase]}</p>
        </div>

        {phase === "done" && onReset && (
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <RotateCcw className="size-3" />
            Download again
          </button>
        )}
      </div>

      {phase !== "done" && (
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-label="Download progress"
        >
          <div className="h-full w-1/4 animate-indeterminate-bar rounded-full bg-primary" />
        </div>
      )}

      {phase === "done" && (
        <p className="text-xs text-muted-foreground">
          Your browser is saving the file to your Downloads folder.
        </p>
      )}
    </div>
  );
}

export function phaseClassName(phase: DownloadPhase): string {
  return cn(phase === "done" && "border-emerald-500/30");
}
