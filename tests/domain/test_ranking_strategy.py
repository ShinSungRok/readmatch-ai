import pytest

from readmatch_ai.domain.ranking_strategy import RankingStrategy


def test_ranking_strategy_is_abstract() -> None:
    with pytest.raises(TypeError):
        RankingStrategy()  # type: ignore[abstract]
