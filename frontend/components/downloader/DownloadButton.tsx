"use client";

import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DownloadButtonProps {
  downloading: boolean;
  disabled: boolean;
  onDownload: () => void;
  label?: string;
  sublabel?: string;
}

export function DownloadButton({
  downloading,
  disabled,
  onDownload,
  label = "Download Now",
  sublabel,
}: DownloadButtonProps) {
  return (
    <Button
      type="button"
      size="lg"
      onClick={onDownload}
      disabled={disabled || downloading}
      className="group relative flex h-12 w-full sm:w-auto sm:min-w-60 items-center justify-center gap-2.5 rounded-xl px-7 py-3 text-base font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98] cursor-pointer"
    >
      {downloading ? (
        <>
          <Loader2 className="size-5 animate-spin" aria-hidden />
          <span>Preparing download…</span>
        </>
      ) : (
        <>
          <Download className="size-5 transition-transform group-hover:translate-y-0.5" aria-hidden />
          <div className="flex flex-col items-center sm:items-start leading-tight">
            <span>{label}</span>
            {sublabel && (
              <span className="text-[11px] font-normal opacity-85">
                {sublabel}
              </span>
            )}
          </div>
        </>
      )}
    </Button>
  );
}
