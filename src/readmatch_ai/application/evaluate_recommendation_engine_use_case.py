from __future__ import annotations

from collections.abc import Mapping

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation import EvaluationDataset, EvaluationResult
from readmatch_ai.domain.evaluation_metrics import (
    average_precision_at_k,
    catalog_coverage,
    diversity_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    novelty_at_k,
    precision_at_k,
    recall_at_k,
)
from readmatch_ai.domain.recommendation import RecommendationQuery
from readmatch_ai.domain.recommendation_engine import RecommendationEngine


class EvaluateRecommendationEngineUseCase:
    """Runs the common offline ranking-evaluation pipeline against any RecommendationEngine.

    Stateless and parametrized per call (rather than constructor-injected
    with one fixed engine, unlike the other recommendation use cases) since
    its purpose is comparing multiple engines against the same dataset.

    `catalog_size`/`popularity_by_book_id` are optional, additive inputs
    (Sprint 30): supplying them also computes `coverage`/`novelty_at_k` on
    the returned EvaluationResult; omitting them (every pre-Sprint-30 call
    site) leaves those two fields None, exactly as before.
    """

    def execute(
        self,
        recommendation_engine: RecommendationEngine,
        engine_name: str,
        dataset: EvaluationDataset,
        k: int,
        catalog_size: int | None = None,
        popularity_by_book_id: Mapping[BookId, int] | None = None,
    ) -> EvaluationResult:
        precision_scores: list[float] = []
        recall_scores: list[float] = []
        average_precision_scores: list[float] = []
        ndcg_scores: list[float] = []
        hit_rate_scores: list[float] = []
        diversity_scores: list[float] = []
        novelty_scores: list[float] = []
        all_recommended_book_ids: list[BookId] = []
        catalog_total_popularity = (
            sum(popularity_by_book_id.values()) if popularity_by_book_id else 0
        )

        for case in dataset.cases:
            query = RecommendationQuery(limit=k, book_id=case.book_id, user_id=case.user_id)
            result = recommendation_engine.recommend(query)
            recommended = [item.book.id for item in result.recommendation.items]
            categories = [item.book.category.value for item in result.recommendation.items]

            precision_scores.append(precision_at_k(recommended, case.relevant_book_ids, k))
            recall_scores.append(recall_at_k(recommended, case.relevant_book_ids, k))
            average_precision_scores.append(
                average_precision_at_k(recommended, case.relevant_book_ids, k)
            )
            ndcg_scores.append(ndcg_at_k(recommended, case.relevant_book_ids, k))
            hit_rate_scores.append(hit_rate_at_k(recommended, case.relevant_book_ids, k))
            diversity_scores.append(diversity_at_k(categories, k))
            all_recommended_book_ids.extend(recommended)

            if popularity_by_book_id is not None:
                popularity_counts = [
                    popularity_by_book_id.get(book_id, 0) for book_id in recommended
                ]
                case_novelty = novelty_at_k(popularity_counts, catalog_total_popularity, k)
                if case_novelty is not None:
                    novelty_scores.append(case_novelty)

        coverage = (
            catalog_coverage(all_recommended_book_ids, catalog_size)
            if catalog_size is not None
            else None
        )
        novelty = _mean(novelty_scores) if novelty_scores else None

        return EvaluationResult(
            engine_name=engine_name,
            k=k,
            precision_at_k=_mean(precision_scores),
            recall_at_k=_mean(recall_scores),
            map_at_k=_mean(average_precision_scores),
            ndcg_at_k=_mean(ndcg_scores),
            hit_rate_at_k=_mean(hit_rate_scores),
            diversity_at_k=_mean(diversity_scores),
            case_count=len(dataset.cases),
            coverage=coverage,
            novelty_at_k=novelty,
        )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
