"use client";

import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ErrorMessageProps {
  message: string;
}

/** Map backend error codes to friendly, actionable messages. */
function friendlyMessage(code: string, message: string): string {
  switch (code) {
    case "UNSUPPORTED_URL":
    case "UNSUPPORTED_PLATFORM":
      return "This URL isn't from a supported platform. Try a YouTube or Instagram reel link.";
    case "MEDIA_NOT_FOUND":
    case "MEDIA_UNAVAILABLE":
      return "Unable to process this URL. Please check the URL and make sure the content is publicly accessible and that you have permission to download it.";
    case "PRIVATE_CONTENT":
      return "This content appears to be private. The app only works with publicly accessible media you are authorized to download.";
    case "RATE_LIMITED":
      return "You're making requests too quickly. Please wait a moment and try again.";
    case "NETWORK_ERROR":
      return "Could not reach the server. Make sure the backend is running and try again.";
    default:
      return message || "Something went wrong. Please try again.";
  }
}

export function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <Alert variant="destructive">
      <AlertCircle aria-hidden />
      <div>
        <AlertTitle>Unable to process this URL</AlertTitle>
        <AlertDescription>
          <p>{message}</p>
          <p className="mt-1 text-destructive/80">
            Please check the URL and make sure the content is publicly
            accessible and that you have permission to download it.
          </p>
        </AlertDescription>
      </div>
    </Alert>
  );
}

export { friendlyMessage };
