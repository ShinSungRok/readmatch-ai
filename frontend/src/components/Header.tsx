"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`transition-colors hover:text-foreground ${
        active ? "font-semibold text-foreground" : "text-zinc-600 dark:text-zinc-400"
      }`}
    >
      {label}
    </Link>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-black/10 bg-white/80 backdrop-blur dark:border-white/15 dark:bg-black/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-1.5 text-lg font-semibold tracking-tight">
          ReadMatch<span className="text-zinc-400 dark:text-zinc-500"> AI</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <NavLink href="/" label="Home" />
          <NavLink href="/search" label="Search" />
          <NavLink href="/library" label="My Library" />
        </nav>
      </div>
    </header>
  );
}
