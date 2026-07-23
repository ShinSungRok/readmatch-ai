"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearInteraction,
  getPersonalLibrary,
  recordInteraction,
  type Interaction,
  type InteractionType,
} from "@/lib/api";
import { getOrCreateAnonymousUserId } from "@/lib/anonymousUser";

function interactionKey(bookId: string, type: InteractionType): string {
  return `${bookId}:${type}`;
}

interface InteractionContextValue {
  userId: string | null;
  /** Count of recorded interactions currently known for this user (cold-start signal). */
  interactionCount: number;
  /**
   * Increments after every successful load/record/clear -- lets a
   * personalized-recommendation consumer re-fetch exactly when this
   * user's interaction history actually changed, without polling.
   */
  revision: number;
  /** The current value for a (book, type) pair, or undefined if not set. */
  getInteraction: (bookId: string, type: InteractionType) => Interaction | undefined;
  /** True while a record/clear call for this exact (book, type) is in flight. */
  isPending: (bookId: string, type: InteractionType) => boolean;
  /** True if the most recent record/clear call for this (book, type) failed. */
  hasError: (bookId: string, type: InteractionType) => boolean;
  /**
   * Toggles a state-like interaction: records it if absent (or, for
   * `rating`, if the given value differs from the current one), clears it
   * if already set to the same value. A no-op while already pending for
   * the same (book, type) -- prevents accidental duplicate submissions
   * from a double click.
   */
  toggle: (bookId: string, type: InteractionType, value?: number) => Promise<void>;
}

const InteractionContext = createContext<InteractionContextValue | null>(null);

export function InteractionProvider({ children }: { children: ReactNode }) {
  // Computed during the initial render, not an effect: getOrCreateAnonymousUserId
  // touches localStorage, so it must stay guarded for the server-rendered
  // pass, but it doesn't affect this component's own rendered markup (only
  // context value consumed by descendants' *behaviour*), so computing it
  // eagerly on the client -- instead of via a post-mount setState, which
  // would need an effect -- introduces no hydration mismatch. Idempotent
  // (reads back the same id on a second call), so React's dev-mode double
  // invocation of lazy initializers is harmless.
  const [userId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : getOrCreateAnonymousUserId(),
  );
  const [interactions, setInteractions] = useState<Map<string, Interaction>>(new Map());
  const [pendingKeys, setPendingKeys] = useState<Set<string>>(new Set());
  const [errorKeys, setErrorKeys] = useState<Set<string>>(new Set());
  const [revision, setRevision] = useState(0);

  const loadInteractions = useCallback((id: string) => {
    getPersonalLibrary(id)
      .then((library) => {
        const next = new Map<string, Interaction>();
        for (const section of library.sections) {
          for (const item of section.items) {
            next.set(interactionKey(item.book.id, item.interaction_type), {
              user_id: id,
              book_id: item.book.id,
              interaction_type: item.interaction_type,
              value: item.value,
            });
          }
        }
        setInteractions(next);
        setRevision((r) => r + 1);
      })
      .catch(() => {
        // The library failing to preload is not fatal -- controls simply
        // start in the "not set" state; individual toggles still work.
      });
  }, []);

  useEffect(() => {
    if (userId) {
      loadInteractions(userId);
    }
  }, [userId, loadInteractions]);

  const toggle = useCallback(
    async (bookId: string, type: InteractionType, value?: number) => {
      if (!userId) {
        return;
      }
      const key = interactionKey(bookId, type);
      if (pendingKeys.has(key)) {
        return;
      }
      const current = interactions.get(key);
      const alreadySet = current !== undefined && (type !== "rating" || current.value === value);

      setPendingKeys((prev) => new Set(prev).add(key));
      setErrorKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
      try {
        if (alreadySet) {
          await clearInteraction(userId, bookId, type);
          setInteractions((prev) => {
            const next = new Map(prev);
            next.delete(key);
            return next;
          });
        } else {
          const recorded = await recordInteraction(userId, bookId, type, value);
          setInteractions((prev) => new Map(prev).set(key, recorded));
        }
        setRevision((r) => r + 1);
      } catch {
        setErrorKeys((prev) => new Set(prev).add(key));
      } finally {
        setPendingKeys((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
      }
    },
    [userId, interactions, pendingKeys],
  );

  const value = useMemo<InteractionContextValue>(
    () => ({
      userId,
      interactionCount: interactions.size,
      revision,
      getInteraction: (bookId, type) => interactions.get(interactionKey(bookId, type)),
      isPending: (bookId, type) => pendingKeys.has(interactionKey(bookId, type)),
      hasError: (bookId, type) => errorKeys.has(interactionKey(bookId, type)),
      toggle,
    }),
    [userId, interactions, revision, pendingKeys, errorKeys, toggle],
  );

  return <InteractionContext.Provider value={value}>{children}</InteractionContext.Provider>;
}

export function useInteractions(): InteractionContextValue {
  const context = useContext(InteractionContext);
  if (!context) {
    throw new Error("useInteractions must be used within an InteractionProvider");
  }
  return context;
}
