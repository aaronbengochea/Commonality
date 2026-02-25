import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Send } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center px-4 pt-16 text-center">
      <Logo size={450} variant="default" />

      <h1 className="mt-12 pb-4 bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-5xl font-bold tracking-tight text-transparent sm:text-6xl">
        Break the Language Barrier
      </h1>

      <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">
        Chat and call anyone in the world — in your native language.
        Commonality translates your messages and voice in real time,
        so the conversation just flows.
      </p>

      <div className="mt-10 flex flex-col items-center gap-4">
        <Link
          href="/login"
          className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-indigo-500 to-pink-500 px-8 py-3 text-lg font-semibold text-white shadow-lg transition-all hover:from-indigo-600 hover:to-pink-600 hover:shadow-xl"
        >
          Get Started
        </Link>
      </div>

      {/* Preview Mockups */}
      <div className="mt-20 w-full max-w-4xl">
        <p className="mb-8 text-sm font-medium uppercase tracking-widest text-muted-foreground">
          See it in action
        </p>
        <div className="grid gap-6 md:grid-cols-2">

          {/* Brian's Chat — All English */}
          <div className="glass-card overflow-hidden p-0 text-left">
            <div className="flex items-center gap-3 border-b border-white/5 px-4 py-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-pink-500/20 text-sm font-semibold text-pink-400">
                M
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Maria</p>
                <p className="text-[10px] text-muted-foreground">Online</p>
              </div>
            </div>

            <div className="space-y-3 px-4 py-4">
              <div className="flex justify-end">
                <div className="flex max-w-[75%] flex-col">
                  <div className="rounded-2xl bg-gradient-to-r from-indigo-500 to-pink-600 px-4 py-2.5">
                    <p className="text-sm text-white">Hey, how&apos;s the project going?</p>
                  </div>
                  <span className="mt-1 text-right text-[10px] text-muted-foreground">2:34 PM</span>
                </div>
              </div>

              <div className="flex justify-start">
                <div className="flex max-w-[75%] flex-col">
                  <div className="glass-bubble px-4 py-2.5">
                    <p className="text-sm text-foreground">It&apos;s going great! We finished the first phase yesterday.</p>
                  </div>
                  <span className="mt-1 text-[10px] text-muted-foreground">2:35 PM</span>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="flex max-w-[75%] flex-col">
                  <div className="rounded-2xl bg-gradient-to-r from-indigo-500 to-pink-600 px-4 py-2.5">
                    <p className="text-sm text-white">That&apos;s awesome! When do we start phase 2?</p>
                  </div>
                  <span className="mt-1 text-right text-[10px] text-muted-foreground">2:35 PM</span>
                </div>
              </div>

              <div className="flex justify-start">
                <div className="flex max-w-[75%] flex-col">
                  <div className="glass-bubble px-4 py-2.5">
                    <p className="text-sm text-foreground">Next week</p>
                  </div>
                  <span className="mt-1 text-[10px] text-muted-foreground">2:36 PM</span>
                </div>
              </div>
            </div>

            <div className="border-t border-white/5 px-4 py-3">
              <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                <span className="flex-1 text-sm text-white/40">Type a message...</span>
                <Send className="h-4 w-4 text-white/30" />
              </div>
            </div>
          </div>

          {/* Maria's Chat — All Spanish */}
          <div className="glass-card overflow-hidden p-0 text-left">
            <div className="flex items-center gap-3 border-b border-white/5 px-4 py-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-semibold text-indigo-400">
                B
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Brian</p>
                <p className="text-[10px] text-muted-foreground">En línea</p>
              </div>
            </div>

            <div className="space-y-3 px-4 py-4">
              <div className="flex justify-start">
                <div className="flex max-w-[75%] flex-col">
                  <div className="glass-bubble px-4 py-2.5">
                    <p className="text-sm text-foreground">Oye, ¿cómo va el proyecto?</p>
                  </div>
                  <span className="mt-1 text-[10px] text-muted-foreground">2:34 PM</span>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="flex max-w-[75%] flex-col">
                  <div className="rounded-2xl bg-gradient-to-r from-indigo-500 to-pink-600 px-4 py-2.5">
                    <p className="text-sm text-white">¡Va genial! Terminamos la primera fase ayer.</p>
                  </div>
                  <span className="mt-1 text-right text-[10px] text-muted-foreground">2:35 PM</span>
                </div>
              </div>

              <div className="flex justify-start">
                <div className="flex max-w-[75%] flex-col">
                  <div className="glass-bubble px-4 py-2.5">
                    <p className="text-sm text-foreground">¡Qué bien! ¿Cuándo empezamos la fase 2?</p>
                  </div>
                  <span className="mt-1 text-[10px] text-muted-foreground">2:35 PM</span>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="flex max-w-[75%] flex-col">
                  <div className="rounded-2xl bg-gradient-to-r from-indigo-500 to-pink-600 px-4 py-2.5">
                    <p className="text-sm text-white">La próxima semana</p>
                  </div>
                  <span className="mt-1 text-right text-[10px] text-muted-foreground">2:36 PM</span>
                </div>
              </div>
            </div>

            <div className="border-t border-white/5 px-4 py-3">
              <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                <span className="flex-1 text-sm text-white/40">Escribe un mensaje...</span>
                <Send className="h-4 w-4 text-white/30" />
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
