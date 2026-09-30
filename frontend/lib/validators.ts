import { z } from "zod";

const SUPPORTED_HOSTS = [
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "youtu.be",
  "instagram.com",
  "www.instagram.com",
] as const;

function isSupportedUrl(value: string): boolean {
  try {
    const parsed = new URL(value.trim());
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
    const host = parsed.hostname.toLowerCase();
    return (SUPPORTED_HOSTS as readonly string[]).some(
      (allowed) => host === allowed || host.endsWith(`.${allowed}`)
    );
  } catch {
    return false;
  }
}

export const urlSchema = z.object({
  url: z
    .string()
    .trim()
    .min(1, "Please paste a media URL.")
    .max(2048, "That URL is too long.")
    .refine((value) => {
      try {
        // eslint-disable-next-line no-new
        new URL(value);
        return true;
      } catch {
        return false;
      }
    }, "Please enter a valid URL.")
    .refine(isSupportedUrl, "Only YouTube and Instagram reel URLs are supported."),
});

export type UrlFormValues = z.infer<typeof urlSchema>;

/** Human-friendly label for the platform value returned by the API. */
export function getPlatformLabel(platform: string): string {
  const lower = platform.toLowerCase();
  if (lower.includes("instagram")) return "Instagram Reel";
  if (lower.includes("youtube")) return "YouTube";
  return platform;
}
