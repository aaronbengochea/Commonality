"use client";

import Link from "next/link";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/Logo";

interface NavbarProps {
  username: string;
  firstName?: string;
  onLogout: () => void;
}

export default function Navbar({ username, firstName, onLogout }: NavbarProps) {
  return (
    <header className="glass-card sticky top-0 z-50 flex items-center justify-between rounded-none border-x-0 border-t-0 px-6 py-3">
      <Link href="/chat" className="flex items-center gap-2">
        <Logo size={36} variant="icon-only" />
        <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-pink-500 bg-clip-text text-lg font-bold text-transparent">
          Commonality
        </span>
      </Link>

      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">
          {firstName && <span className="text-foreground">{firstName}</span>}
          {firstName && " "}
          <span className="text-muted-foreground">@{username}</span>
        </span>
        <Button variant="ghost" size="sm" onClick={onLogout}>
          <LogOut className="mr-1.5 h-4 w-4" />
          Sign out
        </Button>
      </div>
    </header>
  );
}
