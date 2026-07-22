"""Sprint 46 regression tests: explicit feedback (Sprint 44) integrated into
GET /recommendations/personalized/{user_id} via ExplicitFeedbackPolicy.
"""

import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_popularity import BookPopularity


def _register(application_context: ApplicationContext, isbn: str, title: str) -> Book:
    return application_context.register_book_use_case.execute(
        RegisterBookInput(isbn=isbn, title=title, author="An Author", category="Fiction")
    )


def _seed_popularity(application_context: ApplicationContext, book: Book, loan_count: int) -> None:
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count, "2024-01-01", "2024-01-31")
    )


def test_baseline_is_unchanged_for_a_user_with_no_recorded_feedback(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """A user_id that has never recorded any interaction must see exactly
    the same result as before Sprint 46 -- ExplicitFeedbackPolicy is a
    complete no-op without recorded feedback.
    """
    a = _register(application_context, "978-3-16-148410-0", "A")
    b = _register(application_context, "0-306-40615-2", "B")
    _seed_popularity(application_context, a, 100)
    _seed_popularity(application_context, b, 50)
    user_id = str(uuid.uuid4())

    response = client.get(f"/recommendations/personalized/{user_id}")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["book"]["id"] for item in items] == [str(a.id.value), str(b.id.value)]
    assert all(item["source"] == "hybrid" for item in items)


def test_liking_a_book_strengthens_its_score(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """"Positive feedback may strengthen relevant recommendations": liking a
    book must not lower or exclude it, and must measurably raise its score
    relative to itself before the like was recorded. (A full rank flip
    against a much more popular book isn't asserted here -- with only two
    candidates and one active signal, min-max normalization already pins
    scores near the 0/1 extremes regardless of the actual popularity gap,
    which would make any fixed boost's ability to flip the order an
    artifact of this test's fixture size, not of the policy itself; see
    test_reranking_policies.py for a rank-flip assertion under
    isolated/controlled scores.)
    """
    liked = _register(application_context, "978-3-16-148410-0", "Liked")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, liked, 100)
    _seed_popularity(application_context, other, 90)
    user_id = str(uuid.uuid4())

    before_items = client.get(f"/recommendations/personalized/{user_id}").json()["items"]
    before_score = next(
        item["score"] for item in before_items if item["book"]["id"] == str(liked.id.value)
    )

    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(liked.id.value), "interaction_type": "like"},
    )
    after_items = client.get(f"/recommendations/personalized/{user_id}").json()["items"]
    after_score = next(
        item["score"] for item in after_items if item["book"]["id"] == str(liked.id.value)
    )

    assert after_score > before_score
    assert str(liked.id.value) in [item["book"]["id"] for item in after_items]


def test_disliking_a_book_excludes_it_from_results(
    client: TestClient, application_context: ApplicationContext
) -> None:
    disliked = _register(application_context, "978-3-16-148410-0", "Disliked")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, disliked, 100)
    _seed_popularity(application_context, other, 50)
    user_id = str(uuid.uuid4())

    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(disliked.id.value), "interaction_type": "dislike"},
    )
    response = client.get(f"/recommendations/personalized/{user_id}")

    item_ids = [item["book"]["id"] for item in response.json()["items"]]
    assert str(disliked.id.value) not in item_ids
    assert str(other.id.value) in item_ids


def test_marking_a_book_read_excludes_it_from_discovery_recommendations(
    client: TestClient, application_context: ApplicationContext
) -> None:
    read = _register(application_context, "978-3-16-148410-0", "Already Read")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, read, 100)
    _seed_popularity(application_context, other, 50)
    user_id = str(uuid.uuid4())

    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(read.id.value), "interaction_type": "read"},
    )
    response = client.get(f"/recommendations/personalized/{user_id}")

    item_ids = [item["book"]["id"] for item in response.json()["items"]]
    assert str(read.id.value) not in item_ids


def test_a_high_rating_strengthens_a_books_score_like_a_like_does(
    client: TestClient, application_context: ApplicationContext
) -> None:
    rated = _register(application_context, "978-3-16-148410-0", "Rated")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, rated, 100)
    _seed_popularity(application_context, other, 90)
    user_id = str(uuid.uuid4())
    before_items = client.get(f"/recommendations/personalized/{user_id}").json()["items"]
    before_score = next(
        item["score"] for item in before_items if item["book"]["id"] == str(rated.id.value)
    )

    client.post(
        "/interactions",
        json={
            "user_id": user_id,
            "book_id": str(rated.id.value),
            "interaction_type": "rating",
            "value": 5,
        },
    )
    after_items = client.get(f"/recommendations/personalized/{user_id}").json()["items"]
    after_score = next(
        item["score"] for item in after_items if item["book"]["id"] == str(rated.id.value)
    )

    assert after_score > before_score


def test_a_low_rating_excludes_a_book_like_a_dislike_does(
    client: TestClient, application_context: ApplicationContext
) -> None:
    rated = _register(application_context, "978-3-16-148410-0", "Poorly Rated")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, rated, 100)
    _seed_popularity(application_context, other, 50)
    user_id = str(uuid.uuid4())

    client.post(
        "/interactions",
        json={
            "user_id": user_id,
            "book_id": str(rated.id.value),
            "interaction_type": "rating",
            "value": 1,
        },
    )
    response = client.get(f"/recommendations/personalized/{user_id}")

    item_ids = [item["book"]["id"] for item in response.json()["items"]]
    assert str(rated.id.value) not in item_ids


def test_repeated_execution_with_identical_state_is_deterministic(
    client: TestClient, application_context: ApplicationContext
) -> None:
    liked = _register(application_context, "978-3-16-148410-0", "Liked")
    other = _register(application_context, "0-306-40615-2", "Other")
    _seed_popularity(application_context, liked, 100)
    _seed_popularity(application_context, other, 50)
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(liked.id.value), "interaction_type": "like"},
    )

    first = client.get(f"/recommendations/personalized/{user_id}").json()
    second = client.get(f"/recommendations/personalized/{user_id}").json()

    assert first == second


def test_a_single_personalized_request_reports_exactly_one_execution(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """ExplicitFeedbackPolicy runs inside the same, already-observed
    reranked engine -- it must not cause a second recommend() call/metric
    record for one HTTP request.
    """
    book = _register(application_context, "978-3-16-148410-0", "A")
    _seed_popularity(application_context, book, 100)
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(book.id.value), "interaction_type": "like"},
    )
    before = application_context.recommendation_metrics_collector.snapshot().request_count

    client.get(f"/recommendations/personalized/{user_id}")

    after = application_context.recommendation_metrics_collector.snapshot().request_count
    assert after == before + 1
