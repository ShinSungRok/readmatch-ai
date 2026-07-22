import type { HomeFeedItem } from "@/lib/api";
import { BookCard } from "@/components/BookCard";

export function RecommendationRow({
  title,
  description,
  items,
}: {
  title: string;
  description?: string;
  items: HomeFeedItem[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {description ? (
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
      ) : null}
      <ul className="mt-4 flex snap-x gap-4 overflow-x-auto pb-2">
        {items.map((item, index) => (
          <BookCard key={item.book.id} item={item} rank={index + 1} />
        ))}
      </ul>
    </section>
  );
}
