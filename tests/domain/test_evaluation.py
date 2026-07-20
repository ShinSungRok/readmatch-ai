import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset


def test_evaluation_case_rejects_empty_relevant_book_ids() -> None:
    with pytest.raises(ValueError, match="relevant_book_ids"):
        EvaluationCase(book_id=BookId.generate(), relevant_book_ids=frozenset())


def test_evaluation_case_constructs_with_relevant_book_ids() -> None:
    book_id = BookId.generate()
    relevant = frozenset({BookId.generate()})

    case = EvaluationCase(book_id=book_id, relevant_book_ids=relevant)

    assert case.book_id == book_id
    assert case.relevant_book_ids == relevant


def test_evaluation_dataset_rejects_empty_cases() -> None:
    with pytest.raises(ValueError, match="cases"):
        EvaluationDataset(cases=())


def test_evaluation_dataset_constructs_with_cases() -> None:
    case = EvaluationCase(
        book_id=BookId.generate(), relevant_book_ids=frozenset({BookId.generate()})
    )

    dataset = EvaluationDataset(cases=(case,))

    assert dataset.cases == (case,)
