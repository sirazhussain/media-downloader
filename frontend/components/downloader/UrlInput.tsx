"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Search, Youtube, Instagram, Zap } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { urlSchema, type UrlFormValues } from "@/lib/validators";

interface UrlInputProps {
  initialUrl?: string;
  loading: boolean;
  onAnalyze: (url: string) => void;
}

const SUPPORTED = [
  { label: "YouTube", icon: Youtube },
  { label: "YouTube Shorts", icon: Zap },
  { label: "Instagram Reels", icon: Instagram },
];

export function UrlInput({ initialUrl = "", loading, onAnalyze }: UrlInputProps) {
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<UrlFormValues>({
    resolver: zodResolver(urlSchema),
    defaultValues: { url: initialUrl },
  });

  React.useEffect(() => {
    setValue("url", initialUrl);
  }, [initialUrl, setValue]);

  const onSubmit = (values: UrlFormValues) => onAnalyze(values.url.trim());

  return (
    <div className="w-full">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex w-full flex-col gap-3 sm:flex-row"
      >
        <div className="flex-1">
          <Input
            {...register("url")}
            type="text"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="Paste a video or reel URL here"
            aria-label="Media URL"
            aria-invalid={!!errors.url}
            disabled={loading}
            className={errors.url ? "border-destructive focus-visible:ring-destructive" : ""}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          disabled={loading}
          className="h-12 sm:w-40"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin" aria-hidden />
              Analyzing
            </>
          ) : (
            <>
              <Search aria-hidden />
              Analyze
            </>
          )}
        </Button>
      </form>

      {errors.url && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {errors.url.message}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <span className="text-xs text-muted-foreground">Supported:</span>
        {SUPPORTED.map(({ label, icon: Icon }) => (
          <Badge key={label} variant="secondary" className="gap-1.5 py-1">
            <Icon className="size-3.5" aria-hidden />
            {label}
          </Badge>
        ))}
      </div>
    </div>
  );
}
