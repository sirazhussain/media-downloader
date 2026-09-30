"use client";

import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DownloadButtonProps {
  downloading: boolean;
  disabled: boolean;
  onDownload: () => void;
}

export function DownloadButton({
  downloading,
  disabled,
  onDownload,
}: DownloadButtonProps) {
  return (
    <Button
      type="button"
      size="lg"
      onClick={onDownload}
      disabled={disabled || downloading}
      className="w-full sm:w-auto sm:min-w-56"
    >
      {downloading ? (
        <>
          <Loader2 className="animate-spin" aria-hidden />
          Preparing download…
        </>
      ) : (
        <>
          <Download aria-hidden />
          Download
        </>
      )}
    </Button>
  );
}
