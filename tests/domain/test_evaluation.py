import pytest

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.evaluation import EvaluationCase, EvaluationDataset
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
