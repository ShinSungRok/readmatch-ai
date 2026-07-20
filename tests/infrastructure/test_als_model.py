import numpy as np

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.als_model import train_als_model


def _sample_interactions() -> tuple[list[UserBookInteraction], list[UserId], list[BookId]]:
    users = [UserId.generate() for _ in range(3)]
    books = [BookId.generate() for _ in range(4)]
    interactions = [
        UserBookInteraction(users[0], books[0], 5),
        UserBookInteraction(users[0], books[1], 2),
        UserBookInteraction(users[1], books[0], 3),
        UserBookInteraction(users[1], books[2], 1),
        UserBookInteraction(users[2], books[1], 4),
        UserBookInteraction(users[2], books[3], 2),
    ]
    return interactions, users, books


def test_train_als_model_returns_empty_model_for_no_interactions() -> None:
    model = train_als_model([])

    assert model.is_empty
    assert model.user_ids == ()
    assert model.book_ids == ()


def test_train_als_model_indexes_every_distinct_user_and_book() -> None:
    interactions, users, books = _sample_interactions()

    model = train_als_model(interactions, factors=4, iterations=2)

    assert not model.is_empty
    assert set(model.user_ids) == set(users)
    assert set(model.book_ids) == set(books)


def test_train_als_model_produces_factor_matrices_with_matching_shapes() -> None:
    interactions, users, books = _sample_interactions()

    model = train_als_model(interactions, factors=6, iterations=2)

    assert model.user_factors.shape == (len(users), 6)
    assert model.item_factors.shape == (len(books), 6)


def test_train_als_model_is_deterministic_given_a_fixed_random_state() -> None:
    interactions, _, _ = _sample_interactions()

    first = train_als_model(interactions, factors=4, iterations=2, random_state=7)
    second = train_als_model(interactions, factors=4, iterations=2, random_state=7)

    assert first.user_ids == second.user_ids
    assert first.book_ids == second.book_ids
    assert np.array_equal(first.user_factors, second.user_factors)
    assert np.array_equal(first.item_factors, second.item_factors)
