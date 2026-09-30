/**
 * Types mirrored from the FastAPI backend schemas
 * (backend/app/schemas/media.py). Keep in sync.
 */

export interface MediaFormat {
  format_id: string;
  ext: string;
  quality: string;
  width?: number | null;
  height?: number | null;
  filesize?: number | null;
  has_video: boolean;
  has_audio: boolean;
}

export interface MediaInfo {
  platform: string;
  id: string;
  title: string;
  thumbnail?: string | null;
  duration?: number | null;
  uploader?: string | null;
  formats: MediaFormat[];
}

/** Backend error envelope: { error: { code, message } } */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}
