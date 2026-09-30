import Link from "next/link";
import { ArrowLeft, Download } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Downloader } from "@/components/downloader/Downloader";
import { cn } from "@/lib/utils";

interface DownloadPageProps {
  searchParams: { url?: string };
}

export default function DownloadPage({ searchParams }: DownloadPageProps) {
  const url = typeof searchParams.url === "string" ? searchParams.url : "";

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 py-10 sm:px-6 sm:py-16">
      <header className="mb-8 flex items-center justify-between">
        <Link href="/" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
          <ArrowLeft aria-hidden />
          Back
        </Link>
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Download className="size-4" aria-hidden />
          </div>
          <span className="text-sm font-semibold">Media Downloader</span>
        </div>
        <span className="w-16" aria-hidden />
      </header>

      <section>
        <Downloader initialUrl={url} autoAnalyze={url.length > 0} />
      </section>
    </main>
  );
}
