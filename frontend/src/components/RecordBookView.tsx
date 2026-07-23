"use client";

import { useEffect, useRef } from "react";
import { recordInteraction } from "@/lib/api";
import { useInteractions } from "@/components/InteractionProvider";

/**
 * Records a `view` interaction once per Book Detail page load -- an input
 * to the User Preference Profile's recent_interests (Sprint 14). Renders
 * nothing; fire-and-forget (a failed record is not fatal to viewing the
 * page, same convention as InteractionProvider's own library preload).
 */
export function RecordBookView({ bookId }: { bookId: string }) {
  const { userId } = useInteractions();
  const recordedFor = useRef<string | null>(null);

  useEffect(() => {
    if (!userId || recordedFor.current === bookId) {
      return;
    }
    recordedFor.current = bookId;
    void recordInteraction(userId, bookId, "view");
  }, [userId, bookId]);

  return null;
}
