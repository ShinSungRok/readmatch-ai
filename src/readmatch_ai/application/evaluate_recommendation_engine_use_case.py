from __future__ import annotations

from readmatch_ai.domain.evaluation import EvaluationDataset, EvaluationResult
from readmatch_ai.domain.evaluation_metrics import (
    average_precision_at_k,
    hit_rate_at_k,
    ndcg_at_k,
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
    """

    def execute(
        self,
        recommendation_engine: RecommendationEngine,
        engine_name: str,
        dataset: EvaluationDataset,
        k: int,
    ) -> EvaluationResult:
        precision_scores: list[float] = []
        recall_scores: list[float] = []
        average_precision_scores: list[float] = []
        ndcg_scores: list[float] = []
        hit_rate_scores: list[float] = []

        for case in dataset.cases:
            query = RecommendationQuery(limit=k, book_id=case.book_id, user_id=case.user_id)
            result = recommendation_engine.recommend(query)
            recommended = [item.book.id for item in result.recommendation.items]

            precision_scores.append(precision_at_k(recommended, case.relevant_book_ids, k))
            recall_scores.append(recall_at_k(recommended, case.relevant_book_ids, k))
            average_precision_scores.append(
                average_precision_at_k(recommended, case.relevant_book_ids, k)
            )
            ndcg_scores.append(ndcg_at_k(recommended, case.relevant_book_ids, k))
            hit_rate_scores.append(hit_rate_at_k(recommended, case.relevant_book_ids, k))

        return EvaluationResult(
            engine_name=engine_name,
            k=k,
            precision_at_k=_mean(precision_scores),
            recall_at_k=_mean(recall_scores),
            map_at_k=_mean(average_precision_scores),
            ndcg_at_k=_mean(ndcg_scores),
            hit_rate_at_k=_mean(hit_rate_scores),
            case_count=len(dataset.cases),
        )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
