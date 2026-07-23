"use client";

import { useRef } from "react";
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
  const scrollerRef = useRef<HTMLUListElement>(null);

  if (items.length === 0) {
    return null;
  }

  const scrollByCards = (direction: 1 | -1) => {
    scrollerRef.current?.scrollBy({ left: direction * 320, behavior: "smooth" });
  };

  return (
    <section className="group/row">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {description ? (
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
      ) : null}
      <div className="relative mt-4">
        <ul
          ref={scrollerRef}
          className="scrollbar-hide flex snap-x gap-4 overflow-x-auto scroll-smooth pb-2"
        >
          {items.map((item, index) => (
            <BookCard key={item.book.id} item={item} rank={index + 1} />
          ))}
        </ul>
        {/* Trackpad/touch scroll already works without these; they're a
         * pointer-only convenience, hidden on touch-first breakpoints and
         * invisible (but present) until the row is hovered. */}
        <button
          type="button"
          aria-label="Scroll left"
          onClick={() => scrollByCards(-1)}
          className="pointer-events-none absolute inset-y-0 left-0 hidden w-12 items-center justify-start bg-gradient-to-r from-white via-white/80 to-transparent text-xl opacity-0 transition-opacity duration-200 group-hover/row:pointer-events-auto group-hover/row:opacity-100 sm:flex dark:from-zinc-950 dark:via-zinc-950/80"
        >
          <span aria-hidden>‹</span>
        </button>
        <button
          type="button"
          aria-label="Scroll right"
          onClick={() => scrollByCards(1)}
          className="pointer-events-none absolute inset-y-0 right-0 hidden w-12 items-center justify-end bg-gradient-to-l from-white via-white/80 to-transparent text-xl opacity-0 transition-opacity duration-200 group-hover/row:pointer-events-auto group-hover/row:opacity-100 sm:flex dark:from-zinc-950 dark:via-zinc-950/80"
        >
          <span aria-hidden>›</span>
        </button>
      </div>
    </section>
  );
}
