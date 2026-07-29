import { EmptyState } from "@/components/EmptyState";
import { Hero } from "@/components/Hero";
import { OnboardingCategoryPicker } from "@/components/OnboardingCategoryPicker";
import { PersonalizedForYou } from "@/components/PersonalizedForYou";
import { RecommendationRow } from "@/components/RecommendationRow";
import { getHomeFeed } from "@/lib/api";

export default async function HomePage() {
  const homeFeed = await getHomeFeed(12);

  return (
    <div className="flex flex-col gap-10">
      <OnboardingCategoryPicker />

      {!homeFeed.hero ? (
        <EmptyState message="No books have been registered yet." />
      ) : (
        <>
          <Hero item={homeFeed.hero} />
          <div id="recommendations" className="flex scroll-mt-20 flex-col gap-10">
            <PersonalizedForYou />
            {homeFeed.sections.map((section) => (
              <RecommendationRow
                key={section.id}
                title={section.title}
                items={section.items}
                recordsClickAs="recommendation_click"
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
