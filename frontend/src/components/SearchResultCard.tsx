import Link from "next/link";
import type { BookPresentation } from "@/lib/api";
import { BookCover } from "@/components/BookCover";

export function SearchResultCard({ book }: { book: BookPresentation }) {
  const secondaryLine =
    [book.publisher, book.published_date].filter(Boolean).join(" · ") || book.category;

  return (
    <Link href={`/books/${book.id}`} className="group block">
      <div className="aspect-[2/3] w-full overflow-hidden rounded-lg border border-black/10 transition-transform duration-200 ease-out group-hover:z-10 group-hover:scale-[1.06] group-hover:shadow-xl dark:border-white/15">
        <BookCover key={book.cover_url} coverUrl={book.cover_url} />
      </div>
      <div className="mt-2 flex flex-col gap-1">
        <p className="line-clamp-2 text-sm font-medium">{book.title}</p>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">{book.author}</p>
        {secondaryLine ? (
          <p className="line-clamp-1 text-xs text-zinc-400 dark:text-zinc-500">{secondaryLine}</p>
        ) : null}
      </div>
    </Link>
  );
}
