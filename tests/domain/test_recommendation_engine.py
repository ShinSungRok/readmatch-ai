import pytest

from readmatch_ai.domain.recommendation_engine import RecommendationEngine


def test_recommendation_engine_is_abstract() -> None:
    with pytest.raises(TypeError):
        RecommendationEngine()  # type: ignore[abstract]
