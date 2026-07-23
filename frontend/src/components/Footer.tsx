export function Footer() {
  return (
    <footer className="border-t border-black/10 py-8 text-sm text-zinc-500 dark:border-white/15 dark:text-zinc-400">
      <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 sm:px-6">
        <p className="font-medium text-zinc-700 dark:text-zinc-300">ReadMatch AI</p>
        <p>
          AI-powered book recommendations &middot; a personal portfolio project exploring
          popularity, semantic, and hybrid ranking.
        </p>
        <p>Book data courtesy of Data4Library (data4library.kr).</p>
      </div>
    </footer>
  );
}
