import { EmptyState } from "@/components/EmptyState";
import { Hero } from "@/components/Hero";
import { RecommendationRow } from "@/components/RecommendationRow";
import { getHealth, getHomeFeed } from "@/lib/api";

export default async function HomePage() {
  const [health, homeFeed] = await Promise.all([getHealth(), getHomeFeed(12)]);

  return (
    <div className="flex flex-col gap-10">
      <div className="inline-flex w-fit items-center gap-2 rounded-full border border-black/10 px-3 py-1 text-sm dark:border-white/15">
        <span
          aria-hidden
          className={`h-2 w-2 rounded-full ${health.healthy ? "bg-green-500" : "bg-red-500"}`}
        />
        Backend {health.healthy ? "connected" : "unavailable"}
      </div>

      {!homeFeed.hero ? (
        <EmptyState message="No books have been registered yet." />
      ) : (
        <>
          <Hero item={homeFeed.hero} />
          {homeFeed.sections.map((section) => (
            <RecommendationRow key={section.id} title={section.title} items={section.items} />
          ))}
        </>
      )}
    </div>
  );
}
