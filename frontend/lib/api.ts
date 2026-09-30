import { ApiError, type MediaInfo } from "@/types/media";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function readErrorEnvelope(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as Partial<{
      error?: { code?: string; message?: string };
      detail?: string;
    }>;
    if (body.error?.message) {
      return new ApiError(body.error.code ?? "REQUEST_FAILED", body.error.message);
    }
    if (typeof body.detail === "string") {
      return new ApiError("REQUEST_FAILED", body.detail);
    }
  } catch {
    // fall through to generic error
  }
  return new ApiError(
    "REQUEST_FAILED",
    "The server returned an unexpected response. Please try again."
  );
}

function networkError(): ApiError {
  return new ApiError(
    "NETWORK_ERROR",
    "Could not reach the server. Make sure the backend is running and try again."
  );
}

/**
 * Fetch normalized media metadata for a supported URL.
 * Throws ApiError with a user-friendly message on failure.
 */
export async function getMediaInfo(url: string): Promise<MediaInfo> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/media/info`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw networkError();
  }

  if (!res.ok) {
    throw await readErrorEnvelope(res);
  }

  return (await res.json()) as MediaInfo;
}

/**
 * Parse a filename from a Content-Disposition header, supporting
 * plain `filename="..."` and RFC 5987 `filename*=UTF-8''...` forms.
 */
export function parseFilenameFromContentDisposition(
  header: string | null,
  fallback: string
): string {
  if (!header) return fallback;

  const utf8Match = /filename\*\s*=\s*UTF-8''([^;\s]+)/i.exec(header);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      // fall through to plain filename
    }
  }

  const plainMatch = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;\s]+)/i.exec(header);
  const name = plainMatch?.[1] ?? plainMatch?.[2];
  if (name) return name.trim();

  return fallback;
}

/**
 * Download the media for a URL + format id.
 * Returns the binary blob plus the suggested filename.
 * Throws ApiError with a user-friendly message on failure.
 */
export async function downloadMedia(
  url: string,
  formatId: string,
  fallbackFilename?: string
): Promise<{ blob: Blob; filename: string }> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/media/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, format_id: formatId }),
    });
  } catch {
    throw networkError();
  }

  if (!res.ok) {
    throw await readErrorEnvelope(res);
  }

  const blob = await res.blob();
  const filename = parseFilenameFromContentDisposition(
    res.headers.get("content-disposition"),
    fallbackFilename || "download.mp4"
  );

  return { blob, filename };
}

/**
 * Direct download link for native browser download streaming.
 * Bypasses JavaScript blob memory buffering for instant download start.
 */
export function getDirectDownloadUrl(url: string, formatId: string): string {
  return `${API_BASE}/api/v1/media/download?url=${encodeURIComponent(url)}&format_id=${encodeURIComponent(formatId)}`;
}
