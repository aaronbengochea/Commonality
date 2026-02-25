import Link from "next/link";
import { Logo } from "@/components/Logo";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <Logo size={280} variant="default" />

      <h1 className="mt-8 bg-gradient-to-r from-indigo-400 to-pink-500 bg-clip-text text-5xl font-bold tracking-tight text-transparent sm:text-6xl">
        Break the language barrier
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

        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </main>
  );
}
