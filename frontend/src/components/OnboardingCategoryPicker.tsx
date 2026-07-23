"use client";

import { useEffect, useState } from "react";
import { recordPreferenceSignal } from "@/lib/api";
import { useInteractions } from "@/components/InteractionProvider";

const ONBOARDED_STORAGE_KEY = "readmatch-ai:onboarded";

const CATEGORY_OPTIONS = [
  "Fiction",
  "History",
  "Science",
  "Self-Help",
  "Business",
  "Arts",
  "Poetry",
  "Essays",
];

/**
 * First-visit interest onboarding (Sprint 14): a small, dismissible card --
 * not a separate page or account, per this Sprint's "no login/complex
 * member management" constraint. Each selected category is recorded as a
 * `category_interest` PreferenceSignal (GetUserPreferenceProfileUseCase's
 * recent_interests input); "Skip" dismisses without recording anything.
 * Shown at most once per browser (a localStorage flag, the same pattern
 * anonymousUser.ts already uses for the anonymous id itself).
 */
export function OnboardingCategoryPicker() {
  const { userId } = useInteractions();
  // Defaults to true (hidden) on both the server render and the client's
  // hydration pass -- unlike InteractionProvider's own userId (which never
  // changes this component's *rendered markup*), whether this card renders
  // at all *is* the markup, so reading localStorage via a lazy initializer
  // would render different output on the server vs. the client's first
  // (hydration) pass. Corrected right after mount instead -- the standard,
  // hydration-safe "reveal after mount" pattern for client-only UI.
  const [dismissed, setDismissed] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // See the `dismissed` state comment above: this is the deliberate
    // hydration-safe reveal, not state that should instead live in a lazy
    // initializer.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDismissed(window.localStorage.getItem(ONBOARDED_STORAGE_KEY) === "true");
  }, []);

  if (dismissed || !userId) {
    return null;
  }

  const dismiss = () => {
    window.localStorage.setItem(ONBOARDED_STORAGE_KEY, "true");
    setDismissed(true);
  };

  const toggle = (category: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const save = async () => {
    setSubmitting(true);
    try {
      await Promise.all(
        [...selected].map((category) => recordPreferenceSignal(userId, "category_interest", category)),
      );
    } finally {
      dismiss();
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-black/10 p-4 dark:border-white/15">
      <div>
        <p className="font-medium">What are you interested in?</p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Pick a few categories to personalize your recommendations -- you can skip this.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {CATEGORY_OPTIONS.map((category) => {
          const active = selected.has(category);
          return (
            <button
              key={category}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(category)}
              className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                active
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : "border-black/15 text-zinc-600 hover:border-black/30 dark:border-white/20 dark:text-zinc-300"
              }`}
            >
              {category}
            </button>
          );
        })}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={submitting || selected.size === 0}
          onClick={() => void save()}
          className="rounded-full bg-black px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
        >
          Save preferences
        </button>
        <button
          type="button"
          onClick={dismiss}
          className="rounded-full border border-black/15 px-4 py-1.5 text-sm text-zinc-600 transition-colors hover:border-black/30 dark:border-white/20 dark:text-zinc-300"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
