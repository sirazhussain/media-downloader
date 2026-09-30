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
      <footer className="flex flex-col items-center gap-3 pb-8 text-center text-xs text-muted-foreground animate-fade-in" style={{ animationDelay: "300ms", opacity: 0 }}>
        <p className="flex flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-2 leading-relaxed px-4 max-w-md sm:max-w-xl">
          <ShieldCheck className="size-4 shrink-0 text-emerald-500" aria-hidden />
          <span className="text-center">
            Only download media you own or are authorized to use. No files are stored permanently on our servers.
          </span>
        </p>
      </footer>
    </main>
  );
}
