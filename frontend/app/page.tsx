import { Download, Youtube, Instagram, Zap, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Downloader } from "@/components/downloader/Downloader";

const PLATFORMS = [
  { label: "YouTube", icon: Youtube },
  { label: "YouTube Shorts", icon: Zap },
  { label: "Instagram Reels", icon: Instagram },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col items-center gap-4 text-center">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
          <Download className="size-6" aria-hidden />
        </div>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Media Downloader
        </h1>
        <p className="max-w-md text-balance text-muted-foreground">
          Download supported media you own or are authorized to use
        </p>
      </header>

      <section className="mt-10">
        <Downloader />
      </section>

      <section className="mt-10 flex flex-wrap items-center justify-center gap-2">
        {PLATFORMS.map(({ label, icon: Icon }) => (
          <Badge key={label} variant="outline" className="gap-1.5 py-1.5">
            <Icon className="size-4" aria-hidden />
            {label}
          </Badge>
        ))}
      </section>

      <Separator className="my-10" />

      <footer className="flex flex-col items-center gap-3 pb-6 text-center">
        <p className="flex max-w-xl items-start gap-2 text-xs leading-relaxed text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
          Only download content you own or are authorized to download. This
          app does not bypass DRM, paywalls, or private-content restrictions.
        </p>
      </footer>
    </main>
  );
}
