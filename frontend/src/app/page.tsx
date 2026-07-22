import { EmptyState } from "@/components/EmptyState";
import { Hero } from "@/components/Hero";
import { RecommendationRow } from "@/components/RecommendationRow";
import {
  getHealth,
  getHybridRecommendations,
  getPopularityRecommendations,
  getSemanticRecommendations,
  type RecommendationItem,
} from "@/lib/api";
import { buildCategoryRows } from "@/lib/categoryRows";

export default async function HomePage() {
  const [health, popularity] = await Promise.all([
    getHealth(),
    getPopularityRecommendations(12),
  ]);

  const hero: RecommendationItem | undefined = popularity.items[0];

  const [hybrid, similarToHero] = hero
    ? await Promise.all([
        getHybridRecommendations(12),
        getSemanticRecommendations(hero.book.id, 12),
      ])
    : [{ items: [] as RecommendationItem[] }, { items: [] as RecommendationItem[] }];

  const categoryRows = buildCategoryRows([popularity.items, hybrid.items, similarToHero.items]);

  return (
    <div className="flex flex-col gap-10">
      <div className="inline-flex w-fit items-center gap-2 rounded-full border border-black/10 px-3 py-1 text-sm dark:border-white/15">
        <span
          aria-hidden
          className={`h-2 w-2 rounded-full ${health.healthy ? "bg-green-500" : "bg-red-500"}`}
        />
        Backend {health.healthy ? "connected" : "unavailable"}
      </div>

      {!hero ? (
        <EmptyState message="No books have been registered yet." />
      ) : (
        <>
          <Hero item={hero} />
          <RecommendationRow
            title="Popular books"
            description="Ranked by reader loan activity."
            items={popularity.items}
          />
          <RecommendationRow
            title="Recommended picks"
            description="Blended popularity, semantic similarity, and collaborative signals."
            items={hybrid.items}
          />
          <RecommendationRow
            title={`Similar to ${hero.book.title}`}
            items={similarToHero.items}
          />
          {categoryRows.map((row) => (
            <RecommendationRow
              key={row.category}
              title={`More in ${row.category}`}
              items={row.items}
            />
          ))}
        </>
      )}
    </div>
  );
}
