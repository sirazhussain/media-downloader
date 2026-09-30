import { ShieldCheck, Sparkles } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Downloader } from "@/components/downloader/Downloader";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 sm:px-6 lg:px-8 py-8 sm:py-14">
      {/* Header with entrance animation */}
      <header className="flex flex-col items-center gap-3.5 text-center animate-fade-in">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-semibold text-primary shadow-xs animate-bounce-subtle">
          <Sparkles className="size-3.5" />
          <span>Fast, Free & Private</span>
        </div>

        <h1 className="text-3xl tracking-tight sm:text-5xl text-foreground">
          Media Downloader
        </h1>
        <p className="max-w-xl text-balance text-sm sm:text-base text-muted-foreground leading-relaxed">
          Download videos from YouTube, Instagram, LinkedIn, Twitter/X, Facebook & Snapchat — streams directly to your device.
        </p>
      </header>

      {/* Main Downloader */}
      <section className="mt-8 sm:mt-12 animate-fade-in-up" style={{ animationDelay: "150ms", opacity: 0 }}>
        <Downloader />
      </section>

      <Separator className="my-12 opacity-50" />

      {/* Footer */}
      <footer className="mt-8 flex flex-col items-center gap-6 pb-12 w-full animate-fade-in">
        {/* Security & Fair Use Notice Card */}
        <div className="w-full max-w-2xl rounded-2xl border border-border/80 bg-muted/40 backdrop-blur-sm p-4 sm:p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row items-center sm:items-start text-center sm:text-left gap-3.5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="size-5" aria-hidden />
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <span className="text-xs sm:text-sm font-semibold text-foreground">
                  Fair Use & Privacy Policy
                </span>
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  Zero Storage
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed text-balance">
                Only download media you own or have explicit permission to use. We stream media directly to your browser — no videos, audio, or logs are permanently stored on our servers.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Credits & Badges */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 w-full max-w-2xl text-xs text-muted-foreground px-2">
          <span>
            © {new Date().getFullYear()} Media Downloader. Free & Open Source.
          </span>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="inline-flex items-center gap-1">
              <span className="size-1.5 rounded-full bg-emerald-500 inline-block" />
              100% Private
            </span>
            <span>•</span>
            <span>Fast CDN</span>
            <span>•</span>
            <span>Direct Stream</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
