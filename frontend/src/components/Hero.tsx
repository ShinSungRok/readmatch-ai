import type { HomeFeedItem } from "@/lib/api";
import { RecommendationReason } from "@/components/RecommendationReason";

export function Hero({ item }: { item: HomeFeedItem }) {
  const { book } = item;
  return (
    <section className="flex flex-col gap-6 overflow-hidden rounded-2xl border border-black/10 sm:flex-row dark:border-white/15">
      <div className="aspect-[2/3] w-full flex-none sm:w-56">
        <img src={book.cover_url} alt="" aria-hidden className="h-full w-full object-cover" />
      </div>
      <div className="flex flex-col justify-center gap-3 p-6 sm:pl-0">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Top pick
        </span>
        <h2 className="text-2xl font-semibold tracking-tight">{book.title}</h2>
        <p className="text-zinc-600 dark:text-zinc-400">
          {book.author} &middot; {book.category}
        </p>
        {book.description ? (
          <p className="line-clamp-3 text-sm text-zinc-600 dark:text-zinc-400">
            {book.description}
          </p>
        ) : null}
        <RecommendationReason source={item.source} />
      </div>
    </section>
  );
}
