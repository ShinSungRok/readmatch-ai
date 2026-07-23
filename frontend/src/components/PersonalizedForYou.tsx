"use client";

import { useEffect, useState } from "react";
import { useInteractions } from "@/components/InteractionProvider";
import { RecommendationRow } from "@/components/RecommendationRow";
import { getExplainedPersonalizedRecommendations, type HomeFeedItem } from "@/lib/api";

/**
 * Home-page "For You" row, backed by the existing
 * GET /recommendations/personalized/{user_id}/explained endpoint (Sprint
 * 29/46) -- previously implemented and tested, but never called from any
 * page. Re-fetches on `revision` so a Like/Bookmark/Rating recorded via
 * FeedbackControls is visibly reflected without a manual reload, and
 * labels the row as cold-start when this browser has no recorded
 * interactions yet, rather than silently showing the same popularity
 * fallback every other visitor sees.
 */
export function PersonalizedForYou() {
  const { userId, interactionCount, revision } = useInteractions();
  const [items, setItems] = useState<HomeFeedItem[]>([]);

  useEffect(() => {
    if (!userId) {
      return;
    }
    let cancelled = false;
    getExplainedPersonalizedRecommendations(userId, 10)
      .then((result) => {
        if (!cancelled) {
          setItems(result.items);
        }
      })
      .catch(() => {
        // A failed personalized fetch is not fatal to the rest of Home --
        // the row simply stays empty (RecommendationRow renders nothing).
        if (!cancelled) {
          setItems([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [userId, revision]);

  if (!userId || items.length === 0) {
    return null;
  }

  const isColdStart = interactionCount === 0;

  return (
    <RecommendationRow
      title="For You"
      description={
        isColdStart
          ? "Not enough activity yet -- showing popularity-based picks. Like, bookmark, or rate a book to personalize this row."
          : "Personalized using your recorded likes, bookmarks, ratings, and reads."
      }
      items={items}
      recordsClickAs="recommendation_click"
    />
  );
}
