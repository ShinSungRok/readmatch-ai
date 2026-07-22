"use client";

import { useInteractions } from "@/components/InteractionProvider";
import type { InteractionType } from "@/lib/api";

const RATING_VALUES = [1, 2, 3, 4, 5];

const TOGGLES: { type: InteractionType; label: string; activeLabel: string }[] = [
  { type: "like", label: "Like", activeLabel: "Liked" },
  { type: "dislike", label: "Not interested", activeLabel: "Not interested" },
  { type: "bookmark", label: "Bookmark", activeLabel: "Bookmarked" },
  { type: "read", label: "Read", activeLabel: "Marked read" },
];

/**
 * Like/dislike/bookmark/read toggle buttons plus a 1-5 star rating widget
 * for one book, backed by InteractionProvider's shared state (Sprint 47).
 *
 * Every button is disabled while its own request is in flight (prevents
 * duplicate submissions from a double click/tap) and reflects a failed
 * request with a red outline (the state itself already rolled back, since
 * InteractionProvider only ever applies a change after the request
 * succeeds -- never optimistically before).
 */
export function FeedbackControls({ bookId }: { bookId: string }) {
  const { getInteraction, isPending, hasError, toggle } = useInteractions();
  const currentRating = getInteraction(bookId, "rating")?.value ?? null;
  const ratingPending = isPending(bookId, "rating");
  const ratingErrored = hasError(bookId, "rating");

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {TOGGLES.map(({ type, label, activeLabel }) => {
        const active = getInteraction(bookId, type) !== undefined;
        const pending = isPending(bookId, type);
        const errored = hasError(bookId, type);
        return (
          <button
            key={type}
            type="button"
            aria-pressed={active}
            aria-label={active ? activeLabel : label}
            disabled={pending}
            onClick={() => {
              void toggle(bookId, type);
            }}
            className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-colors disabled:cursor-wait disabled:opacity-50 ${
              active
                ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                : "border-black/15 text-zinc-600 hover:border-black/30 dark:border-white/20 dark:text-zinc-300"
            } ${errored ? "border-red-500 text-red-600 dark:text-red-400" : ""}`}
          >
            {label}
          </button>
        );
      })}
      <div
        className={`flex items-center gap-0.5 ${ratingErrored ? "rounded outline outline-red-500" : ""}`}
        role="group"
        aria-label="Rate this book"
      >
        {RATING_VALUES.map((value) => (
          <button
            key={value}
            type="button"
            aria-label={`Rate ${value} out of 5`}
            aria-pressed={currentRating === value}
            disabled={ratingPending}
            onClick={() => {
              void toggle(bookId, "rating", value);
            }}
            className={`text-base leading-none disabled:cursor-wait disabled:opacity-50 ${
              currentRating !== null && value <= currentRating
                ? "text-amber-500"
                : "text-zinc-300 hover:text-amber-400 dark:text-zinc-600"
            }`}
          >
            ★
          </button>
        ))}
      </div>
    </div>
  );
}
