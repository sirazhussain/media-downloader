"""Pydantic schemas for the media API (mirrored by frontend TypeScript types)."""

from pydantic import BaseModel, Field


class MediaInfoRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class MediaFormat(BaseModel):
    format_id: str
    ext: str
    quality: str  # e.g. "720p", "1080p", or "audio" for audio-only
    width: int | None = None
    height: int | None = None
    filesize: int | None = None
    has_video: bool
    has_audio: bool


class MediaInfoResponse(BaseModel):
    platform: str
    id: str
    title: str
    thumbnail: str | None = None
    duration: int | None = None
    uploader: str | None = None
    formats: list[MediaFormat]


class DownloadRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    format_id: str = Field(min_length=1, max_length=64, pattern=r"^[\w\-.]+$")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
