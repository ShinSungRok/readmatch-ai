import Link from "next/link";
import type { HomeFeedItem } from "@/lib/api";
import { BookCover } from "@/components/BookCover";
import { FeedbackControls } from "@/components/FeedbackControls";
import { RecommendationReason } from "@/components/RecommendationReason";

export function Hero({ item }: { item: HomeFeedItem }) {
  const { book } = item;
  const publisherLine = [book.publisher, book.published_date].filter(Boolean).join(" · ");
  return (
    <section className="relative min-h-[480px] overflow-hidden rounded-2xl border border-black/10 sm:min-h-[460px] lg:min-h-[500px] dark:border-white/15">
      {/* Blurred cover as a full-bleed backdrop; cover_url is guaranteed
       * non-empty (deterministic_cover_fallback), and a CSS background-image
       * simply renders nothing extra on a broken/unreachable URL -- no
       * broken-image icon, so no separate fallback handling is needed here. */}
      <div
        aria-hidden
        className="absolute inset-0 scale-110 bg-cover bg-center blur-2xl brightness-50"
        style={{ backgroundImage: `url(${book.cover_url})` }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/70 to-black/30" />
      <div className="absolute inset-0 hidden bg-gradient-to-r from-black/70 via-black/10 to-transparent sm:block" />

      <div className="relative z-10 flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:p-10">
        <div className="hidden w-40 flex-none overflow-hidden rounded-lg shadow-2xl ring-1 ring-white/10 sm:block sm:w-48">
          <div className="aspect-[2/3] w-full">
            <BookCover key={book.cover_url} coverUrl={book.cover_url} />
          </div>
        </div>

        <div className="flex max-w-xl flex-col gap-3 text-white">
          <span className="w-fit rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide backdrop-blur">
            Today&apos;s top pick
          </span>
          <Link href={`/books/${book.id}`} className="hover:underline">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">{book.title}</h2>
          </Link>
          <p className="text-white/80">
            {book.author} &middot; {book.category}
          </p>
          {publisherLine ? <p className="text-sm text-white/60">{publisherLine}</p> : null}
          {book.description ? (
            <p className="line-clamp-3 text-sm text-white/70">{book.description}</p>
          ) : null}

          <div className="mt-1 flex flex-wrap items-center gap-3">
            <Link
              href={`/books/${book.id}`}
              className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-zinc-200"
            >
              View book details
            </Link>
            <a
              href="#recommendations"
              className="rounded-full border border-white/40 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/10"
            >
              Explore recommendations
            </a>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2">
            <div className="w-fit rounded-lg bg-white/90 p-1.5 backdrop-blur dark:bg-zinc-900/70">
              <RecommendationReason source={item.source} />
            </div>
            <div className="w-fit rounded-lg bg-white/90 p-1.5 backdrop-blur dark:bg-zinc-900/70">
              <FeedbackControls bookId={book.id} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
