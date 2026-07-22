import type { RecommendationItem } from "@/lib/api";

const MINIMUM_BOOKS_PER_CATEGORY = 2;

export interface CategoryRow {
  category: string;
  items: RecommendationItem[];
}

/**
 * Groups an already-ranked pool of recommendations by category for display.
 *
 * Pure presentation shaping -- no new ranking/scoring happens here. Each
 * book id is kept once (first occurrence wins), categories with fewer than
 * `MINIMUM_BOOKS_PER_CATEGORY` books are dropped (not useful as a row), and
 * the result is sorted by category name for a deterministic render order.
 */
export function buildCategoryRows(itemLists: RecommendationItem[][]): CategoryRow[] {
  const seenBookIds = new Set<string>();
  const byCategory = new Map<string, RecommendationItem[]>();

  for (const items of itemLists) {
    for (const item of items) {
      if (seenBookIds.has(item.book.id)) {
        continue;
      }
      seenBookIds.add(item.book.id);
      const existing = byCategory.get(item.book.category);
      if (existing) {
        existing.push(item);
      } else {
        byCategory.set(item.book.category, [item]);
      }
    }
  }

  return Array.from(byCategory.entries())
    .filter(([, items]) => items.length >= MINIMUM_BOOKS_PER_CATEGORY)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, items]) => ({ category, items }));
}
