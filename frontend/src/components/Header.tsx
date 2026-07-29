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
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-4 sm:px-6">
        <Link
          href="/"
          className="flex items-baseline gap-1 text-lg font-medium tracking-tight text-zinc-800 dark:text-zinc-100"
        >
          ReadMatch<span className="text-sm font-normal text-zinc-400 dark:text-zinc-500">AI</span>
        </Link>
        {/* flex-wrap on both this row and the nav itself: four labels plus
         * the logo can be tighter than some phone viewports allow on one
         * line -- wrapping to a second line reads far better than a
         * horizontal scrollbar or overlapping/cut-off text. */}
        <nav className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-sm sm:gap-x-4">
          <NavLink href="/" label="Home" />
          <NavLink href="/search" label="Search" />
          <NavLink href="/library" label="My Library" />
          <NavLink href="/preferences" label="My Preferences" />
        </nav>
      </div>
    </header>
  );
}
