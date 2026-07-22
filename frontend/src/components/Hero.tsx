import Link from "next/link";
import type { HomeFeedItem } from "@/lib/api";
import { BookCover } from "@/components/BookCover";
import { FeedbackControls } from "@/components/FeedbackControls";
import { RecommendationReason } from "@/components/RecommendationReason";

export function Hero({ item }: { item: HomeFeedItem }) {
  const { book } = item;
  const publisherLine = [book.publisher, book.published_date].filter(Boolean).join(" · ");
  return (
    <section className="flex flex-col gap-6 overflow-hidden rounded-2xl border border-black/10 sm:flex-row dark:border-white/15">
      <div className="aspect-[2/3] w-full flex-none sm:w-56">
        <BookCover key={book.cover_url} coverUrl={book.cover_url} />
      </div>
      <div className="flex flex-col justify-center gap-3 p-6 sm:pl-0">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Top pick
        </span>
        <Link href={`/books/${book.id}`} className="hover:underline">
          <h2 className="text-2xl font-semibold tracking-tight">{book.title}</h2>
        </Link>
        <p className="text-zinc-600 dark:text-zinc-400">
          {book.author} &middot; {book.category}
        </p>
        {publisherLine ? (
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{publisherLine}</p>
        ) : null}
        {book.description ? (
          <p className="line-clamp-3 text-sm text-zinc-600 dark:text-zinc-400">
            {book.description}
          </p>
        ) : null}
        <RecommendationReason source={item.source} />
        <FeedbackControls bookId={book.id} />
      </div>
    </section>
  );
}
