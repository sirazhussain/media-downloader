"use client";

import * as React from "react";
import { DownloadCloud } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { UrlInput } from "./UrlInput";
import {
  MediaPreview,
  MediaPreviewSkeleton,
} from "./MediaPreview";
import { QualitySelector } from "./QualitySelector";
import { FormatSelectorSkeleton } from "./FormatSelector";
import { DownloadButton } from "./DownloadButton";
import { DownloadProgress, type DownloadPhase } from "./DownloadProgress";
import { ErrorMessage, friendlyMessage } from "./ErrorMessage";
import { getMediaInfo, downloadMedia } from "@/lib/api";
import { ApiError, type MediaInfo } from "@/types/media";

type FlowState = "initial" | "loading" | "ready" | "error";

interface DownloaderProps {
  initialUrl?: string;
  autoAnalyze?: boolean;
}

/** Prefer a combined video+audio format as the default selection. */
function pickDefaultFormat(media: MediaInfo): string | null {
  if (media.formats.length === 0) return null;
  const combined = media.formats.find((f) => f.has_video && f.has_audio);
  return (combined ?? media.formats[0]).format_id;
}

export function Downloader({ initialUrl = "", autoAnalyze = false }: DownloaderProps) {
  const [flowState, setFlowState] = React.useState<FlowState>("initial");
  const [media, setMedia] = React.useState<MediaInfo | null>(null);
  const [url, setUrl] = React.useState(initialUrl);
  const [selectedFormatId, setSelectedFormatId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [downloadPhase, setDownloadPhase] = React.useState<DownloadPhase>("idle");
  const autoAnalyzed = React.useRef(false);

  const analyze = React.useCallback(async (targetUrl: string) => {
    setFlowState("loading");
    setError(null);
    setMedia(null);
    setSelectedFormatId(null);
    setDownloadPhase("idle");
    setUrl(targetUrl);

    try {
      const info = await getMediaInfo(targetUrl);
      setMedia(info);
      setSelectedFormatId(pickDefaultFormat(info));
      setFlowState("ready");
    } catch (err) {
      const apiError = err instanceof ApiError ? err : null;
      setError(
        friendlyMessage(apiError?.code ?? "", apiError?.message ?? "")
      );
      setFlowState("error");
    }
  }, []);

  React.useEffect(() => {
    if (autoAnalyze && initialUrl && !autoAnalyzed.current) {
      autoAnalyzed.current = true;
      void analyze(initialUrl);
    }
  }, [autoAnalyze, initialUrl, analyze]);

  const handleDownload = React.useCallback(async () => {
    if (!media || !selectedFormatId || !url) return;
    setError(null);
    setDownloadPhase("preparing");

    try {
      const selected = media.formats.find((f) => f.format_id === selectedFormatId);
      const ext = selected?.ext || "mp4";
      const fallbackFilename = media.title
        ? `${media.title.replace(/[/\\:*?"<>|]/g, "").trim()}.${ext}`
        : `download.${ext}`;

      const { blob, filename } = await downloadMedia(
        url,
        selectedFormatId,
        fallbackFilename
      );
      setDownloadPhase("downloading");

      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      setDownloadPhase("done");
      // Give the browser a moment to pick up the blob URL before revoking.
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      window.setTimeout(() => setDownloadPhase("idle"), 8000);
    } catch (err) {
      setDownloadPhase("idle");
      const apiError = err instanceof ApiError ? err : null;
      setError(
        friendlyMessage(apiError?.code ?? "", apiError?.message ?? "")
      );
    }
  }, [media, selectedFormatId, url]);

  const selectedFormat = media?.formats.find(
    (f) => f.format_id === selectedFormatId
  );

  return (
    <div className="flex w-full flex-col gap-6">
      <UrlInput
        initialUrl={initialUrl}
        loading={flowState === "loading"}
        onAnalyze={(value) => void analyze(value)}
      />

      {flowState === "loading" && (
        <>
          <MediaPreviewSkeleton />
          <div className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold">Available formats</h3>
            <FormatSelectorSkeleton />
          </div>
        </>
      )}

      {flowState === "error" && error && <ErrorMessage message={error} />}

      {flowState === "ready" && media && (
        <>
          <MediaPreview media={media} />

          <div className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-semibold">Available formats</h3>
              <span className="text-xs text-muted-foreground">
                {media.formats.length} option{media.formats.length === 1 ? "" : "s"}
              </span>
            </div>
            <QualitySelector
              formats={media.formats}
              selectedFormatId={selectedFormatId}
              onSelect={setSelectedFormatId}
              disabled={downloadPhase === "preparing"}
            />
          </div>

          <div className="flex flex-col items-stretch gap-3 sm:items-start w-full sm:max-w-md">
            {downloadPhase === "idle" ? (
              <>
                <DownloadButton
                  downloading={false}
                  disabled={!selectedFormat}
                  onDownload={() => void handleDownload()}
                />
                <p className="text-xs text-muted-foreground">
                  Your download will be saved by your browser.
                </p>
              </>
            ) : (
              <div className="w-full">
                <DownloadProgress
                  phase={downloadPhase}
                  onReset={() => setDownloadPhase("idle")}
                />
              </div>
            )}
          </div>
        </>
      )}

      {flowState === "initial" && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 p-10 text-center">
            <DownloadCloud className="size-8 text-muted-foreground" aria-hidden />
            <p className="text-sm font-medium">Paste a link to get started</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Paste a YouTube or Instagram reel URL above and we&apos;ll fetch
              the available download formats for content you own or are
              authorized to use.
            </p>
          </CardContent>
        </Card>
      )}

      {flowState === "ready" && error && <ErrorMessage message={error} />}
    </div>
  );
}
