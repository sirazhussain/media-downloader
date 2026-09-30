"use client";

import Image from "next/image";
import { Clock, User } from "lucide-react";
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
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div className="flex flex-col sm:flex-row">
          <div className="relative aspect-video w-full shrink-0 bg-muted sm:w-72">
            {media.thumbnail ? (
              <Image
                src={media.thumbnail}
                alt={media.title}
                fill
                className="object-cover"
                sizes="(max-width: 640px) 100vw, 288px"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
                No preview
              </div>
            )}
          </div>
          <div className="flex flex-1 flex-col justify-center gap-3 p-5 sm:p-6">
            <h2 className="line-clamp-2 text-lg font-semibold leading-snug">
              {media.title}
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default">{getPlatformLabel(media.platform)}</Badge>
              <Badge variant="outline" className="gap-1">
                <Clock className="size-3" aria-hidden />
                {formatDuration(media.duration)}
              </Badge>
              {media.uploader && (
                <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
                  <User className="size-3.5" aria-hidden />
                  <span className="max-w-56 truncate">{media.uploader}</span>
                </span>
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
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div className="flex flex-col sm:flex-row">
          <Skeleton className="aspect-video w-full rounded-none sm:w-72" />
          <div className="flex flex-1 flex-col justify-center gap-3 p-5 sm:p-6">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-6 w-1/2" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-24 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
