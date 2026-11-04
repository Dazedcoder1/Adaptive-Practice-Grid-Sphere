"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/button";

const links = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#paths", label: "School · JEE · NEET" },
  { href: "#features", label: "Features" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="bg-background/80 supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40 border-b border-transparent backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Logo />
        <nav className="text-muted-foreground hidden gap-6 text-sm md:flex" aria-label="Main">
          {links.map((l) => (
            <a key={l.href} href={l.href} className="hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="ml-auto hidden gap-2 md:flex">
          <Button asChild variant="ghost">
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild variant="gradient">
            <Link href="/register">Start learning free</Link>
          </Button>
        </div>
        <button
          className="hover:bg-muted ml-auto rounded-md p-2 md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>
      {open && (
        <div className="bg-card border-t px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-3 text-sm" aria-label="Mobile">
            {links.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
                {l.label}
              </a>
            ))}
          </nav>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Button asChild variant="outline">
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild variant="gradient">
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
