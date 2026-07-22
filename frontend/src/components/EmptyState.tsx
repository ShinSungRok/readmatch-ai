export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-black/15 p-8 text-center text-zinc-500 dark:border-white/20 dark:text-zinc-400">
      {message}
    </div>
  );
}
