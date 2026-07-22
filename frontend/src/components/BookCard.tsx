import Link from "next/link";
import type { HomeFeedItem } from "@/lib/api";
import { FeedbackControls } from "@/components/FeedbackControls";
import { RecommendationReason } from "@/components/RecommendationReason";

export function BookCard({ item, rank }: { item: HomeFeedItem; rank?: number }) {
  const { book } = item;
  return (
    <li className="w-40 flex-none snap-start sm:w-44">
      <Link href={`/books/${book.id}`} className="block">
        <div className="relative aspect-[2/3] w-full overflow-hidden rounded-lg border border-black/10 dark:border-white/15">
          <img src={book.cover_url} alt="" aria-hidden className="h-full w-full object-cover" />
          {rank ? (
            <span className="absolute left-2 top-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-semibold text-white">
              #{rank}
            </span>
          ) : null}
        </div>
        <div className="mt-2 flex flex-col gap-1">
          <p className="line-clamp-2 text-sm font-medium">{book.title}</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{book.author}</p>
        </div>
      </Link>
      <div className="mt-1.5 flex flex-col gap-1.5">
        <RecommendationReason source={item.source} />
        <FeedbackControls bookId={book.id} />
      </div>
    </li>
  );
}
