import Link from "next/link";

export function Header() {
  return (
    <header className="border-b border-black/10 dark:border-white/15">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          ReadMatch AI
        </Link>
        <nav className="flex items-center gap-4 text-sm text-zinc-600 dark:text-zinc-400">
          <Link href="/" className="hover:text-foreground">
            Home
          </Link>
          <Link href="/library" className="hover:text-foreground">
            My Library
          </Link>
        </nav>
      </div>
    </header>
  );
}
