"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Loader2,
  Search,
  Youtube,
  Instagram,
  Zap,
  ClipboardPaste,
  X,
  Link as LinkIcon,
} from "lucide-react";
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
  { label: "YouTube", icon: Youtube, color: "text-red-500" },
  { label: "Instagram", icon: Instagram, color: "text-pink-500" },
  { label: "LinkedIn", icon: LinkIcon, color: "text-blue-600" },
  { label: "Twitter / X", icon: Zap, color: "text-sky-500" },
  { label: "Facebook", icon: LinkIcon, color: "text-blue-500" },
  { label: "Snapchat", icon: Zap, color: "text-yellow-400" },
];

export function UrlInput({ initialUrl = "", loading, onAnalyze }: UrlInputProps) {
  const [hasClipboard, setHasClipboard] = React.useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<UrlFormValues>({
    resolver: zodResolver(urlSchema),
    defaultValues: { url: initialUrl },
  });

  const currentUrl = watch("url");

  React.useEffect(() => {
    setValue("url", initialUrl);
  }, [initialUrl, setValue]);

  React.useEffect(() => {
    if (
      typeof window !== "undefined" &&
      "clipboard" in navigator &&
      typeof navigator.clipboard.readText === "function"
    ) {
      setHasClipboard(true);
    }
  }, []);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        setValue("url", text.trim(), { shouldValidate: true });
        onAnalyze(text.trim());
      }
    } catch {
      // Clipboard permission denied or unsupported
    }
  };

  const handleClear = () => {
    setValue("url", "", { shouldValidate: false });
  };

  const onSubmit = (values: UrlFormValues) => onAnalyze(values.url.trim());

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit(onSubmit)} className="w-full">
        <div className="relative flex flex-col gap-2.5 sm:flex-row sm:items-center rounded-2xl border-2 border-border/80 bg-card p-1.5 shadow-sm transition-all focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10">
          <div className="relative flex flex-1 items-center">
            <LinkIcon className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" />
            <Input
              {...register("url")}
              type="text"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              placeholder="Paste a YouTube, Shorts, or Instagram Reel link..."
              aria-label="Media URL"
              aria-invalid={!!errors.url}
              disabled={loading}
              className="h-12 border-0 bg-transparent pl-10 pr-20 text-base shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/70"
            />

            {/* Quick action buttons inside input */}
            <div className="absolute right-2 flex items-center gap-1">
              {currentUrl && (
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={loading}
                  aria-label="Clear input"
                  className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              )}
              {hasClipboard && !currentUrl && (
                <button
                  type="button"
                  onClick={handlePaste}
                  disabled={loading}
                  className="flex items-center gap-1 rounded-lg bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground transition hover:bg-secondary/80 cursor-pointer"
                >
                  <ClipboardPaste className="size-3.5" />
                  <span>Paste</span>
                </button>
              )}
            </div>
          </div>

          <Button
            type="submit"
            size="lg"
            disabled={loading}
            className="h-12 w-full sm:w-auto px-7 font-semibold shrink-0 rounded-xl shadow-sm transition-all hover:shadow"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
                Fetching...
              </>
            ) : (
              <>
                <Search className="mr-2 size-4" aria-hidden />
                Fetch Media
              </>
            )}
          </Button>
        </div>
      </form>

      {errors.url && (
        <p role="alert" className="mt-2.5 px-1 text-sm font-medium text-destructive">
          {errors.url.message}
        </p>
      )}

      {/* Supported Platform Badges */}
      <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-2 px-1">
        <span className="text-xs font-medium text-muted-foreground">Supported:</span>
        {SUPPORTED.map(({ label, icon: Icon, color }) => (
          <Badge
            key={label}
            variant="secondary"
            className="gap-1.5 py-1 px-2.5 text-xs font-normal border border-border/50 bg-secondary/50 hover:bg-secondary transition"
          >
            <Icon className={`size-3.5 ${color}`} aria-hidden />
            {label}
          </Badge>
        ))}
      </div>
    </div>
  );
}
