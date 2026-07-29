"use client";

import { useEffect, useState } from "react";
import { clearPreferenceSignal, recordPreferenceSignal } from "@/lib/api";
import { useInteractions } from "@/components/InteractionProvider";

const ONBOARDED_STORAGE_KEY = "readmatch-ai:onboarded";
const SAVED_CATEGORIES_STORAGE_KEY = "readmatch-ai:preferred-categories";

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

type Phase = "loading" | "hidden" | "picking" | "summary";

function readSavedCategories(): string[] {
  const raw = window.localStorage.getItem(SAVED_CATEGORIES_STORAGE_KEY);
  if (!raw) {
    return [];
  }
  const parsed: unknown = JSON.parse(raw);
  return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
}

/**
 * First-visit interest onboarding (Sprint 14): a small card -- not a
 * separate page or account, per this Sprint's "no login/complex member
 * management" constraint. Each selected category is recorded as a
 * `category_interest` PreferenceSignal (GetUserPreferenceProfileUseCase's
 * recent_interests input); "Skip" dismisses without recording anything.
 *
 * After a save, the card doesn't disappear -- it switches to a compact
 * "summary" state showing the saved categories plus a reset button, so the
 * choice stays visible instead of vanishing without a trace. Reset calls
 * DELETE /preference-signals (clearing every recorded category_interest
 * signal server-side, not just the local copy) and then re-shows the
 * picker.
 */
export function OnboardingCategoryPicker() {
  const { userId } = useInteractions();
  // Defaults to "loading" (hidden) on both the server render and the
  // client's hydration pass -- unlike InteractionProvider's own userId
  // (which never changes this component's *rendered markup*), which phase
  // this card is in *is* the markup, so reading localStorage via a lazy
  // initializer would render different output on the server vs. the
  // client's first (hydration) pass. Corrected right after mount instead --
  // the standard, hydration-safe "reveal after mount" pattern for
  // client-only UI.
  const [phase, setPhase] = useState<Phase>("loading");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [savedCategories, setSavedCategories] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    const onboarded = window.localStorage.getItem(ONBOARDED_STORAGE_KEY) === "true";
    const stored = readSavedCategories();
    // See the `phase` state comment above: this is the deliberate
    // hydration-safe reveal, not state that should instead live in a lazy
    // initializer.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSavedCategories(stored);
    setPhase(!onboarded ? "picking" : stored.length > 0 ? "summary" : "hidden");
  }, []);

  if (phase === "loading" || phase === "hidden" || !userId) {
    return null;
  }

  const skip = () => {
    window.localStorage.setItem(ONBOARDED_STORAGE_KEY, "true");
    setPhase("hidden");
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

  const clearSelection = () => {
    setSelected(new Set());
  };

  const save = async () => {
    setSubmitting(true);
    try {
      await Promise.all(
        [...selected].map((category) => recordPreferenceSignal(userId, "category_interest", category)),
      );
    } finally {
      const savedList = [...selected];
      window.localStorage.setItem(ONBOARDED_STORAGE_KEY, "true");
      window.localStorage.setItem(SAVED_CATEGORIES_STORAGE_KEY, JSON.stringify(savedList));
      setSavedCategories(savedList);
      setSubmitting(false);
      setPhase("summary");
    }
  };

  const resetSaved = async () => {
    setResetting(true);
    try {
      await clearPreferenceSignal(userId, "category_interest");
    } finally {
      window.localStorage.removeItem(ONBOARDED_STORAGE_KEY);
      window.localStorage.removeItem(SAVED_CATEGORIES_STORAGE_KEY);
      setSavedCategories([]);
      setSelected(new Set());
      setResetting(false);
      setPhase("picking");
    }
  };

  if (phase === "summary") {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-black/10 p-4 dark:border-white/15">
        <span className="text-sm text-zinc-500 dark:text-zinc-400">선호 카테고리</span>
        <div className="flex flex-wrap gap-2">
          {savedCategories.map((category) => (
            <span
              key={category}
              className="rounded-full border border-black/15 px-3 py-1 text-sm text-zinc-600 dark:border-white/20 dark:text-zinc-300"
            >
              {category}
            </span>
          ))}
        </div>
        <button
          type="button"
          disabled={resetting}
          onClick={() => void resetSaved()}
          className="ml-auto rounded-full border border-black/15 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-black/30 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/20 dark:text-zinc-300"
        >
          초기화
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-black/10 p-4 dark:border-white/15">
      <div>
        <p className="font-medium">선호하는 카테고리를 선택해 주세요</p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          몇 가지 카테고리를 선택하면 맞춤 추천에 반영돼요. 건너뛰어도 괜찮아요.
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
          선호도 저장
        </button>
        <button
          type="button"
          disabled={submitting || selected.size === 0}
          onClick={clearSelection}
          className="rounded-full border border-black/15 px-4 py-1.5 text-sm text-zinc-600 transition-colors hover:border-black/30 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/20 dark:text-zinc-300"
        >
          선택 초기화
        </button>
        <button
          type="button"
          onClick={skip}
          className="rounded-full border border-black/15 px-4 py-1.5 text-sm text-zinc-600 transition-colors hover:border-black/30 dark:border-white/20 dark:text-zinc-300"
        >
          건너뛰기
        </button>
      </div>
    </div>
  );
}
