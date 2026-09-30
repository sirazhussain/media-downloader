"use client";

import * as React from "react";
import {
  DownloadCloud,
  Zap,
  ShieldCheck,
  Sparkles,
  Smartphone,
  Lock,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
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
import { formatFileSize } from "@/lib/utils";

type FlowState = "initial" | "loading" | "ready" | "error";

interface DownloaderProps {
  initialUrl?: string;
  autoAnalyze?: boolean;
}

/** Default to highest quality video, falling back to first format. */
function pickDefaultFormat(media: MediaInfo): string | null {
  if (media.formats.length === 0) return null;
  const bestVideo = media.formats.find((f) => f.has_video);
  return (bestVideo ?? media.formats[0]).format_id;
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
    <div className="flex w-full flex-col gap-8">
      {/* URL Input Bar */}
      <UrlInput
        initialUrl={initialUrl}
        loading={flowState === "loading"}
        onAnalyze={(value) => void analyze(value)}
      />

      {/* Loading Skeleton */}
      {flowState === "loading" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start animate-slide-in-bottom">
          <div className="lg:col-span-5 animate-pulse-soft">
            <MediaPreviewSkeleton />
          </div>
          <div className="lg:col-span-7 flex flex-col gap-4 animate-fade-in" style={{ animationDelay: "100ms", opacity: 0 }}>
            <div className="h-6 w-40 rounded-lg bg-muted shimmer-bg animate-shimmer" />
            <FormatSelectorSkeleton />
          </div>
        </div>
      )}

      {/* Error Message */}
      {flowState === "error" && error && (
        <div className="animate-scale-in">
          <ErrorMessage message={error} />
        </div>
      )}

      {/* Media & Formats - 2-Column Responsive Layout */}
      {flowState === "ready" && media && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start animate-slide-in-bottom">
          {/* Left Column: Media Card + Quick Info */}
          <div className="lg:col-span-5 flex flex-col gap-4 lg:sticky lg:top-6 animate-fade-in">
            <MediaPreview media={media} />

            {/* Quick Summary Card */}
            {selectedFormat && (
              <div className="hidden lg:flex flex-col gap-2.5 rounded-2xl border border-border/80 glass p-4 text-xs shadow-sm card-hover animate-fade-in" style={{ animationDelay: "200ms", opacity: 0 }}>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Selected Quality:</span>
                  <span className="font-semibold text-foreground">
                    {selectedFormat.quality} ({selectedFormat.ext.toUpperCase()})
                  </span>
                </div>
                {selectedFormat.filesize && (
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>Est. File Size:</span>
                    <span className="font-semibold text-foreground">
                      {formatFileSize(selectedFormat.filesize)}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Format Type:</span>
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">
                    {selectedFormat.has_video
                      ? "Video (Audio Included)"
                      : "Audio Only"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Format Selector + Action Button */}
          <div className="lg:col-span-7 flex flex-col gap-5 rounded-2xl border border-border/80 glass p-5 sm:p-6 shadow-sm animate-fade-in-up" style={{ animationDelay: "150ms", opacity: 0 }}>
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground">Choose Quality & Format</h3>
              <span className="text-xs font-medium text-muted-foreground">
                {media.formats.length} formats available
              </span>
            </div>

            <QualitySelector
              formats={media.formats}
              selectedFormatId={selectedFormatId}
              onSelect={setSelectedFormatId}
              disabled={downloadPhase === "preparing"}
            />

            {/* Download Action Section */}
            <div className="mt-2 border-t border-border/60 pt-5">
              {downloadPhase === "idle" ? (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                    <DownloadButton
                      downloading={false}
                      disabled={!selectedFormat}
                      onDownload={() => void handleDownload()}
                      label="Download Media"
                      sublabel={
                        selectedFormat
                          ? `${selectedFormat.quality} • ${selectedFormat.ext.toUpperCase()}`
                          : undefined
                      }
                    />
                  </div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <ShieldCheck className="size-3.5 text-emerald-500" />
                    Direct streaming • No files saved on server
                  </p>
                </div>
              ) : (
                <div className="w-full">
                  <DownloadProgress
                    phase={downloadPhase}
                    onReset={() => setDownloadPhase("idle")}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Initial Landing State: Rich Features & Instructions */}
      {flowState === "initial" && (
        <div className="flex flex-col gap-10 mt-2 animate-fade-in-up" style={{ animationDelay: "100ms", opacity: 0 }}>
          {/* 3 Step Visual Guide */}
          <div className="flex flex-col gap-4">
            <div className="text-center sm:text-left">
              <h2 className="text-lg font-bold text-foreground">How it works</h2>
              <p className="text-sm text-muted-foreground">
                Download media you own in 3 simple steps
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 stagger-children">
              <div className="flex flex-col gap-2 rounded-2xl border border-border/80 bg-card p-5 shadow-sm card-hover">
                <div className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                  1
                </div>
                <h3 className="font-semibold text-sm text-foreground">Copy & Paste Link</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Copy any video URL from YouTube, Instagram, LinkedIn, Twitter/X, Facebook, or Snapchat and paste it above.
                </p>
              </div>

              <div className="flex flex-col gap-2 rounded-2xl border border-border/80 bg-card p-5 shadow-sm card-hover">
                <div className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                  2
                </div>
                <h3 className="font-semibold text-sm text-foreground">Pick Format & Quality</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Choose from 1080p FHD, 720p HD, 480p, or extract MP3 audio directly.
                </p>
              </div>

              <div className="flex flex-col gap-2 rounded-2xl border border-border/80 bg-card p-5 shadow-sm card-hover">
                <div className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary font-bold text-sm">
                  3
                </div>
                <h3 className="font-semibold text-sm text-foreground">Instant Download</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Click download and the media streams straight into your browser download folder.
                </p>
              </div>
            </div>
          </div>

          {/* Value Props & Benefits */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-border/60 pt-8 stagger-children">
            <div className="flex items-start gap-3 card-hover rounded-xl p-3 -m-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600">
                <Zap className="size-4" />
              </div>
              <div className="flex flex-col gap-1">
                <h4 className="text-sm font-semibold text-foreground">High Speed Streaming</h4>
                <p className="text-xs text-muted-foreground">
                  Direct chunked streaming without slow server queuing.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 card-hover rounded-xl p-3 -m-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600">
                <Lock className="size-4" />
              </div>
              <div className="flex flex-col gap-1">
                <h4 className="text-sm font-semibold text-foreground">100% Private</h4>
                <p className="text-xs text-muted-foreground">
                  No tracking, no logs of downloads, zero files stored permanently.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 card-hover rounded-xl p-3 -m-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
                <Smartphone className="size-4" />
              </div>
              <div className="flex flex-col gap-1">
                <h4 className="text-sm font-semibold text-foreground">Mobile & Desktop</h4>
                <p className="text-xs text-muted-foreground">
                  Fully responsive on all iOS, Android, and desktop browsers.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {flowState === "ready" && error && <ErrorMessage message={error} />}
    </div>
  );
}
