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
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 sm:px-6 lg:px-8 py-8 sm:py-14">
      <header className="mb-8 flex items-center justify-between">
        <Link href="/" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "gap-1.5")}>
          <ArrowLeft className="size-4" aria-hidden />
          Back
        </Link>
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Download className="size-4" aria-hidden />
          </div>
          <span className="text-base font-bold">Media Downloader</span>
        </div>
        <span className="w-16" aria-hidden />
      </header>

      <section>
        <Downloader initialUrl={url} autoAnalyze={url.length > 0} />
      </section>
    </main>
  );
}
