import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation import (
    EvaluationCase,
    EvaluationDataset,
    split_dataset,
)
from readmatch_ai.domain.user import UserId


def test_evaluation_case_rejects_empty_relevant_book_ids() -> None:
    with pytest.raises(ValueError, match="relevant_book_ids"):
        EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset())


def test_evaluation_case_rejects_neither_book_id_nor_user_id() -> None:
    with pytest.raises(ValueError, match="book_id or user_id"):
        EvaluationCase(relevant_book_ids=frozenset({BookId.generate()}))


def test_evaluation_case_constructs_with_book_id() -> None:
    book_id = BookId.generate()
    relevant = frozenset({BookId.generate()})

    case = EvaluationCase(book_id=book_id, relevant_book_ids=relevant)

    assert case.book_id == book_id
    assert case.user_id is None
    assert case.relevant_book_ids == relevant


def test_evaluation_case_constructs_with_user_id() -> None:
    user_id = UserId.generate()
    relevant = frozenset({BookId.generate()})

    case = EvaluationCase(user_id=user_id, relevant_book_ids=relevant)

    assert case.user_id == user_id
    assert case.book_id is None
    assert case.relevant_book_ids == relevant


def test_evaluation_case_constructs_with_both_book_id_and_user_id() -> None:
    book_id = BookId.generate()
    user_id = UserId.generate()
    relevant = frozenset({BookId.generate()})

    case = EvaluationCase(book_id=book_id, user_id=user_id, relevant_book_ids=relevant)

    assert case.book_id == book_id
    assert case.user_id == user_id


def test_evaluation_dataset_rejects_empty_cases() -> None:
    with pytest.raises(ValueError, match="cases"):
        EvaluationDataset(cases=())


def test_evaluation_dataset_constructs_with_cases() -> None:
    case = EvaluationCase(
        book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()})
    )

    dataset = EvaluationDataset(cases=(case,))

    assert dataset.cases == (case,)


def _cases(count: int) -> tuple[EvaluationCase, ...]:
    return tuple(
        EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()}))
        for _ in range(count)
    )


def test_split_dataset_partitions_every_case_exactly_once() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    split = split_dataset(dataset, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15)

    all_split_cases = split.train.cases + split.validation.cases + split.test.cases
    assert len(all_split_cases) == 20
    assert set(all_split_cases) == set(dataset.cases)
    assert len(set(all_split_cases)) == 20  # no case appears in more than one split


def test_split_dataset_respects_the_requested_ratios() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    split = split_dataset(dataset, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15)

    assert len(split.train.cases) == 14
    assert len(split.validation.cases) == 3
    assert len(split.test.cases) == 3


def test_split_dataset_is_deterministic_given_the_same_seed() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    first = split_dataset(dataset, seed=42)
    second = split_dataset(dataset, seed=42)

    assert first.train.cases == second.train.cases
    assert first.validation.cases == second.validation.cases
    assert first.test.cases == second.test.cases


def test_split_dataset_different_seeds_can_produce_different_splits() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    first = split_dataset(dataset, seed=1)
    second = split_dataset(dataset, seed=2)

    assert first.train.cases != second.train.cases


def test_split_dataset_rejects_ratios_that_do_not_sum_to_one() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    with pytest.raises(ValueError, match="sum to 1.0"):
        split_dataset(dataset, train_ratio=0.5, validation_ratio=0.2, test_ratio=0.2)


def test_split_dataset_rejects_a_non_positive_ratio() -> None:
    dataset = EvaluationDataset(cases=_cases(20))

    with pytest.raises(ValueError, match="positive"):
        split_dataset(dataset, train_ratio=1.0, validation_ratio=0.0, test_ratio=0.0)


def test_split_dataset_rejects_a_dataset_too_small_for_a_non_empty_split() -> None:
    dataset = EvaluationDataset(cases=_cases(2))

    with pytest.raises(ValueError, match="too small"):
        split_dataset(dataset, train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15)


def test_split_dataset_default_ratios_split_the_demo_sized_dataset() -> None:
    """Regression check against this project's real 8-case demo dataset
    size (scripts/demo_fixtures.build_evaluation_dataset), so a future
    change to the default ratios can't silently make the demo dataset
    unsplittable without a test failing here first."""
    dataset = EvaluationDataset(cases=_cases(8))

    split = split_dataset(dataset)

    assert len(split.train.cases) + len(split.validation.cases) + len(split.test.cases) == 8
    assert split.train.cases and split.validation.cases and split.test.cases
