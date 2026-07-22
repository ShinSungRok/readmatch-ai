from __future__ import annotations

import random
from dataclasses import dataclass

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId


@dataclass(frozen=True)
class EvaluationCase:
    """One evaluation query and the books considered relevant to it.

    Exactly mirrors RecommendationQuery's optional book_id/user_id split: a
    book-similarity case (Semantic/Hybrid) sets book_id, a personalized case
    (ALS) sets user_id, and a case may set both to evaluate an engine that
    uses either/both. Deliberately decoupled from how relevance was derived
    (category overlap, held-out interactions, curated fixtures) — the
    evaluation pipeline only needs the resulting set.
    """

    relevant_book_ids: frozenset[BookId]
    book_id: BookId | None = None
    user_id: UserId | None = None

    def __post_init__(self) -> None:
        if not self.relevant_book_ids:
            raise ValueError("relevant_book_ids must not be empty")
        if self.book_id is None and self.user_id is None:
            raise ValueError("EvaluationCase requires at least one of book_id or user_id")


@dataclass(frozen=True)
class EvaluationDataset:
    """A deterministic collection of EvaluationCases to evaluate a RecommendationEngine against."""

    cases: tuple[EvaluationCase, ...]

    def __post_init__(self) -> None:
        if not self.cases:
            raise ValueError("cases must not be empty")


@dataclass(frozen=True)
class DatasetSplit:
    """A dataset partitioned into train/validation/test EvaluationDatasets.

    Every case from the source dataset appears in exactly one split (no
    overlap, no drops) -- see split_dataset()'s own docstring for the
    partitioning rule.
    """

    train: EvaluationDataset
    validation: EvaluationDataset
    test: EvaluationDataset


def split_dataset(
    dataset: EvaluationDataset,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 0,
) -> DatasetSplit:
    """Deterministically partition `dataset` into train/validation/test splits.

    Ratios must be positive and sum to 1.0 (within floating-point
    tolerance) -- a caller-visible ValueError otherwise, rather than a
    silently-renormalized split. Case order is shuffled with a
    seed-derived `random.Random` before partitioning (never Python's
    global random state), so:
    - the split is reproducible: the same dataset + seed always produces
      byte-identical train/validation/test contents, run to run;
    - it isn't biased by the source dataset's own case ordering (e.g.
      cases grouped by book category, as scripts/demo_fixtures.py
      produces them) -- without shuffling, a contiguous slice could put
      an entire category only in one split.

    Split sizes are computed by `floor(n * ratio)` for train and
    validation, with every remaining case (covering any rounding
    shortfall) going to test, so the three splits always sum to exactly
    `len(dataset.cases)`. Raises ValueError if any resulting split would
    be empty (EvaluationDataset itself does not allow empty `cases`) --
    a dataset too small for the requested ratios is a caller error to
    surface immediately, not silently skip a split for.
    """
    if train_ratio <= 0 or validation_ratio <= 0 or test_ratio <= 0:
        raise ValueError("train_ratio, validation_ratio, and test_ratio must all be positive")
    if abs((train_ratio + validation_ratio + test_ratio) - 1.0) > 1e-9:
        raise ValueError(
            "train_ratio + validation_ratio + test_ratio must sum to 1.0, got "
            f"{train_ratio + validation_ratio + test_ratio!r}"
        )

    cases = list(dataset.cases)
    random.Random(seed).shuffle(cases)

    total = len(cases)
    train_count = int(total * train_ratio)
    validation_count = int(total * validation_ratio)
    train_cases = cases[:train_count]
    validation_cases = cases[train_count : train_count + validation_count]
    test_cases = cases[train_count + validation_count :]

    if not train_cases or not validation_cases or not test_cases:
        raise ValueError(
            f"dataset of {total} case(s) is too small to split at ratios "
            f"({train_ratio}, {validation_ratio}, {test_ratio}) without an empty split"
        )

    return DatasetSplit(
        train=EvaluationDataset(cases=tuple(train_cases)),
        validation=EvaluationDataset(cases=tuple(validation_cases)),
        test=EvaluationDataset(cases=tuple(test_cases)),
    )


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregate ranking-quality metrics for one RecommendationEngine over an EvaluationDataset.

    Each *_at_k field is the mean of that metric across all cases in the
    dataset, so results from different engines (or different k) are directly
    comparable. `coverage` and `novelty_at_k` are None when the caller didn't
    supply the extra evidence they need (catalog_size / popularity data,
    respectively) -- distinguishing "not computed" from a fabricated 0.0.
    """

    engine_name: str
    k: int
    precision_at_k: float
    recall_at_k: float
    map_at_k: float
    ndcg_at_k: float
    hit_rate_at_k: float
    diversity_at_k: float
    case_count: int
    coverage: float | None = None
    novelty_at_k: float | None = None
