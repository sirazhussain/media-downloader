"use client";

import Image from "next/image";
import { Clock, User, Youtube, Instagram, Film } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getPlatformLabel } from "@/lib/validators";
import { formatDuration } from "@/lib/utils";
import type { MediaInfo } from "@/types/media";

interface MediaPreviewProps {
  media: MediaInfo;
}

export function MediaPreview({ media }: MediaPreviewProps) {
  const isInstagram = media.platform?.toLowerCase().includes("instagram");

  return (
    <Card className="overflow-hidden border border-border/80 bg-card shadow-sm transition hover:shadow-md">
      <CardContent className="p-0">
        <div className="flex flex-col">
          {/* Thumbnail Container */}
          <div className="relative aspect-video w-full overflow-hidden bg-muted/60">
            {media.thumbnail ? (
              <Image
                src={media.thumbnail}
                alt={media.title}
                fill
                priority
                className="object-cover transition-transform duration-300 hover:scale-105"
                sizes="(max-width: 1024px) 100vw, 480px"
              />
            ) : (
              <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
                <Film className="size-8 stroke-1 text-muted-foreground/60" />
                <span>No preview available</span>
              </div>
            )}

            {/* Platform Badge Overlay */}
            <div className="absolute left-3 top-3">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold text-white shadow-md backdrop-blur-md ${
                  isInstagram
                    ? "bg-gradient-to-r from-purple-600 via-pink-600 to-amber-500"
                    : "bg-red-600"
                }`}
              >
                {isInstagram ? (
                  <Instagram className="size-3.5" />
                ) : (
                  <Youtube className="size-3.5" />
                )}
                {getPlatformLabel(media.platform)}
              </span>
            </div>

            {/* Duration Badge Overlay */}
            {media.duration ? (
              <div className="absolute bottom-3 right-3">
                <span className="inline-flex items-center gap-1 rounded-md bg-black/80 px-2 py-0.5 text-xs font-medium text-white shadow-sm backdrop-blur-sm">
                  <Clock className="size-3" />
                  {formatDuration(media.duration)}
                </span>
              </div>
            ) : null}
          </div>

          {/* Details Section */}
          <div className="flex flex-col gap-2.5 p-4 sm:p-5">
            <h2 className="line-clamp-2 text-base sm:text-lg font-semibold leading-snug text-foreground">
              {media.title}
            </h2>

            <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/50 text-xs text-muted-foreground">
              {media.uploader && (
                <span className="inline-flex items-center gap-1.5 font-medium text-foreground/80">
                  <User className="size-3.5 text-primary" aria-hidden />
                  <span className="truncate max-w-[200px] sm:max-w-xs">{media.uploader}</span>
                </span>
              )}
              {media.formats && (
                <Badge variant="outline" className="text-xs font-normal">
                  {media.formats.length} formats available
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function MediaPreviewSkeleton() {
  return (
    <Card className="overflow-hidden border border-border/80 bg-card">
      <CardContent className="p-0">
        <div className="flex flex-col">
          <Skeleton className="aspect-video w-full rounded-none" />
          <div className="flex flex-col gap-3 p-4 sm:p-5">
            <Skeleton className="h-6 w-5/6" />
            <Skeleton className="h-4 w-3/5" />
            <div className="flex gap-2 pt-1">
              <Skeleton className="h-5 w-24 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
