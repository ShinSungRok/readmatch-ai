import uuid

from fastapi.testclient import TestClient

from readmatch_ai.api.dependencies import get_application_context
from readmatch_ai.api.main import create_app
from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.book_popularity import BookPopularity
from readmatch_ai.domain.user import UserId
from readmatch_ai.domain.user_book_interaction import UserBookInteraction
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_user_book_interaction_repository import (
    InMemoryUserBookInteractionRepository,
)


def _valid_input() -> RegisterBookInput:
    return RegisterBookInput(
        isbn="978-3-16-148410-0",
        title="Clean Code",
        author="Robert C. Martin",
        category="Software Engineering",
    )


def _other_input() -> RegisterBookInput:
    return RegisterBookInput(
        isbn="0-306-40615-2",
        title="Effective Java",
        author="Joshua Bloch",
        category="Software Engineering",
    )


def test_popularity_recommendations_reflect_persisted_popularity(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get("/recommendations/popularity", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(book.id.value)
    assert body["items"][0]["source"] == "popularity"
    assert body["items"][0]["score"] == 100.0


def test_popularity_recommendations_returns_empty_list_when_no_data(client: TestClient) -> None:
    response = client.get("/recommendations/popularity")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_popularity_recommendations_rejects_non_positive_limit(client: TestClient) -> None:
    response = client.get("/recommendations/popularity", params={"limit": 0})

    assert response.status_code == 422


def test_popularity_recommendations_rejects_limit_above_max(client: TestClient) -> None:
    response = client.get("/recommendations/popularity", params={"limit": 101})

    assert response.status_code == 422


def test_semantic_recommendations_reflect_persisted_embeddings(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(other.id.value)
    assert body["items"][0]["source"] == "semantic"
    # The source book itself must never appear in its own recommendations.
    assert all(item["book"]["id"] != str(source.id.value) for item in body["items"])


def test_semantic_recommendations_returns_empty_list_for_book_with_no_embedding(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())

    response = client.get(f"/recommendations/semantic/{source.id.value}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_semantic_recommendations_rejects_a_malformed_book_id(client: TestClient) -> None:
    response = client.get("/recommendations/semantic/not-a-uuid")

    assert response.status_code == 400
    assert "detail" in response.json()


def test_hybrid_recommendations_combine_popularity_and_semantic_signals(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))
    application_context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(
        "/recommendations/hybrid", params={"book_id": str(source.id.value), "limit": 10}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(other.id.value)
    assert body["items"][0]["source"] == "hybrid"


def test_hybrid_recommendations_work_without_a_source_book(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=50, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get("/recommendations/hybrid")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(book.id.value)


def test_hybrid_recommendations_rejects_a_malformed_book_id(client: TestClient) -> None:
    response = client.get("/recommendations/hybrid", params={"book_id": "not-a-uuid"})

    assert response.status_code == 400


def test_hybrid_recommendations_accept_an_optional_user_id(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """user_id is a new, optional parameter (Sprint 28): backward compatible
    with every existing call site that never passed one, and a valid but
    unknown user degrades gracefully rather than erroring -- same as an
    omitted book_id already does.
    """
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=50, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(
        "/recommendations/hybrid", params={"user_id": str(uuid.uuid4()), "limit": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(book.id.value)


def test_hybrid_recommendations_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.get("/recommendations/hybrid", params={"user_id": "not-a-uuid"})

    assert response.status_code == 400


# --- GET /recommendations/personalized/{user_id} ---


def test_personalized_recommendations_blend_hybrid_signals(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))
    application_context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}",
        params={"book_id": str(source.id.value), "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["book"]["id"] == str(other.id.value)
    # Re-ranking preserves the underlying engine's `source` label.
    assert body["items"][0]["source"] == "hybrid"


def test_personalized_recommendations_preserve_the_requested_count(
    client: TestClient, application_context: ApplicationContext
) -> None:
    isbns = [
        "978-3-16-148410-0",
        "0-306-40615-2",
        "9780132350884",
        "978-0-13-468599-1",
        "978-0-596-00712-6",
        "9791165341909",
    ]
    books = [
        application_context.register_book_use_case.execute(
            RegisterBookInput(isbn=isbn, title=f"Title {i}", author="Author", category="Category")
        )
        for i, isbn in enumerate(isbns)
    ]
    for book in books:
        application_context.generate_book_embedding_use_case.execute(str(book.id.value))
    source = books[0]

    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}",
        params={"book_id": str(source.id.value), "limit": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert all(item["book"]["id"] != str(source.id.value) for item in body["items"])


def test_personalized_recommendations_boost_a_novel_book_over_a_known_one(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """Sanity-checks that the re-ranking stage's NoveltyBoostPolicy is
    actually reached through this endpoint. NoveltyBoostPolicy reads the
    interaction repository live, per request (unlike ALS, which trains
    eagerly at ApplicationContext.create() time), so recording an
    interaction inside this test body -- after the shared client/
    application_context fixtures already exist -- still takes effect.
    """
    known = application_context.register_book_use_case.execute(_valid_input())
    unknown = application_context.register_book_use_case.execute(_other_input())
    application_context.book_popularity_repository.record(
        BookPopularity(known.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )
    application_context.book_popularity_repository.record(
        BookPopularity(
            unknown.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31"
        )
    )
    user_id = uuid.uuid4()
    application_context.user_book_interaction_repository.record(
        UserBookInteraction(UserId(user_id), known.id, interaction_count=1)
    )

    response = client.get(f"/recommendations/personalized/{user_id}", params={"limit": 2})

    assert response.status_code == 200
    items = response.json()["items"]
    scores_by_book_id = {item["book"]["id"]: item["score"] for item in items}
    assert scores_by_book_id[str(unknown.id.value)] > scores_by_book_id[str(known.id.value)]


def test_personalized_recommendations_reflect_als_signal_from_seeded_interactions() -> None:
    """ALS trains once, eagerly, at ApplicationContext.create() time (see
    application_context.py), so interactions must be recorded *before* the
    context (and this test's own client) is built -- this test constructs
    its own context/client rather than using the shared fixtures, mirroring
    tests/test_application_context.py::test_als_recommendations_exclude_already_interacted_books.
    """
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    liked = Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Liked"),
        author=Author("Author"),
        category=Category("Category"),
    )
    unseen = Book(
        id=BookId.generate(),
        isbn=ISBN("0-306-40615-2"),
        title=Title("Unseen"),
        author=Author("Author"),
        category=Category("Category"),
    )
    book_repository.add(liked)
    book_repository.add(unseen)

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    interaction_repository.record(UserBookInteraction(UserId(user_id), liked.id, 5))
    interaction_repository.record(UserBookInteraction(UserId(other_user_id), liked.id, 4))
    interaction_repository.record(UserBookInteraction(UserId(other_user_id), unseen.id, 3))

    context = ApplicationContext.create(
        book_repository=book_repository, user_book_interaction_repository=interaction_repository
    )
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    with TestClient(app) as als_client:
        response = als_client.get(f"/recommendations/personalized/{user_id}", params={"limit": 10})

    assert response.status_code == 200
    recommended_ids = {item["book"]["id"] for item in response.json()["items"]}
    # ALS excludes books the user already interacted with; `liked` must not
    # reappear even though it's the only book with any recorded popularity/
    # semantic signal for this user to otherwise latch onto.
    assert str(liked.id.value) not in recommended_ids


def test_personalized_recommendations_returns_empty_list_for_an_unknown_user(
    client: TestClient,
) -> None:
    # A well-formed but never-seen user_id: no interactions, no ALS
    # membership -- graceful fallback (200, empty when there's also no
    # other data), not a 404.
    response = client.get(f"/recommendations/personalized/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_personalized_recommendations_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.get("/recommendations/personalized/not-a-uuid")

    assert response.status_code == 400
    assert "detail" in response.json()


def test_personalized_recommendations_rejects_non_positive_limit(client: TestClient) -> None:
    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}", params={"limit": 0}
    )

    assert response.status_code == 422


def test_personalized_recommendations_rejects_limit_above_max(client: TestClient) -> None:
    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}", params={"limit": 101}
    )

    assert response.status_code == 422


def test_semantic_recommendations_returns_empty_list_for_a_nonexistent_book_id(
    client: TestClient,
) -> None:
    # A well-formed but unregistered book id: no embedding can exist for it,
    # so this behaves the same as "book has no embedding yet" (200, empty),
    # not a 404 -- consistent with the underlying SemanticRecommendationEngine.
    response = client.get(f"/recommendations/semantic/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


# --- GET /recommendations/personalized/{user_id}/explained ---


def test_explained_recommendations_include_a_popularity_reason(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(f"/recommendations/personalized/{uuid.uuid4()}/explained")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    reason_types = [reason["type"] for reason in items[0]["reasons"]]
    assert "popularity" in reason_types
    assert items[0]["reasons"][reason_types.index("popularity")]["message"] == (
        "Popular with many readers."
    )


def test_explained_recommendations_include_a_semantic_similarity_reason_when_book_id_is_present(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))

    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}/explained",
        params={"book_id": str(source.id.value)},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["book"]["id"] == str(other.id.value)
    reason_types = [reason["type"] for reason in items[0]["reasons"]]
    assert "semantic_similarity" in reason_types


def test_explained_recommendations_omit_semantic_reason_without_a_source_book(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(f"/recommendations/personalized/{uuid.uuid4()}/explained")

    assert response.status_code == 200
    items = response.json()["items"]
    reason_types = [reason["type"] for item in items for reason in item["reasons"]]
    assert "semantic_similarity" not in reason_types


def test_explained_recommendations_include_a_novelty_reason_for_an_unknown_user(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get(f"/recommendations/personalized/{uuid.uuid4()}/explained")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    reason_types = [reason["type"] for reason in items[0]["reasons"]]
    assert "novelty" in reason_types


def test_explained_recommendations_omit_novelty_reason_for_an_already_interacted_book(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )
    user_id = uuid.uuid4()
    application_context.user_book_interaction_repository.record(
        UserBookInteraction(UserId(user_id), book.id, interaction_count=1)
    )

    response = client.get(f"/recommendations/personalized/{user_id}/explained")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    reason_types = [reason["type"] for reason in items[0]["reasons"]]
    assert "novelty" not in reason_types


def test_explained_recommendations_include_a_diversity_reason_where_evidence_supports_it(
    client: TestClient, application_context: ApplicationContext
) -> None:
    same_category_a = application_context.register_book_use_case.execute(
        RegisterBookInput(
            isbn="978-3-16-148410-0", title="A", author="Author", category="Fiction"
        )
    )
    same_category_b = application_context.register_book_use_case.execute(
        RegisterBookInput(
            isbn="0-306-40615-2", title="B", author="Author", category="Fiction"
        )
    )
    different_category = application_context.register_book_use_case.execute(
        RegisterBookInput(
            isbn="9780132350884", title="C", author="Author", category="History"
        )
    )
    for book, loan_count in (
        (same_category_a, 100),
        (same_category_b, 90),
        (different_category, 80),
    ):
        application_context.book_popularity_repository.record(
            BookPopularity(book.id, loan_count, "2024-01-01", "2024-01-31")
        )

    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}/explained", params={"limit": 3}
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    reason_types_by_book_id = {
        item["book"]["id"]: [reason["type"] for reason in item["reasons"]] for item in items
    }
    # The first item of a batch never gets "diversity" (nothing precedes it
    # to be diverse relative to); the first item whose category hasn't
    # appeared yet in the batch does.
    assert "diversity" not in reason_types_by_book_id[items[0]["book"]["id"]]
    assert "diversity" in reason_types_by_book_id[str(different_category.id.value)]


def test_explained_recommendations_reflect_als_signal_from_seeded_interactions() -> None:
    """ALS trains once, eagerly, at ApplicationContext.create() time, so
    interactions must be recorded *before* the context (and this test's own
    client) is built -- mirrors
    test_personalized_recommendations_reflect_als_signal_from_seeded_interactions.
    """
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryUserBookInteractionRepository()
    liked = Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Liked"),
        author=Author("Author"),
        category=Category("Category"),
    )
    unseen = Book(
        id=BookId.generate(),
        isbn=ISBN("0-306-40615-2"),
        title=Title("Unseen"),
        author=Author("Author"),
        category=Category("Category"),
    )
    book_repository.add(liked)
    book_repository.add(unseen)

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    interaction_repository.record(UserBookInteraction(UserId(user_id), liked.id, 5))
    interaction_repository.record(UserBookInteraction(UserId(other_user_id), liked.id, 4))
    interaction_repository.record(UserBookInteraction(UserId(other_user_id), unseen.id, 3))

    context = ApplicationContext.create(
        book_repository=book_repository, user_book_interaction_repository=interaction_repository
    )
    app = create_app()
    app.dependency_overrides[get_application_context] = lambda: context
    with TestClient(app) as als_client:
        response = als_client.get(f"/recommendations/personalized/{user_id}/explained")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["book"]["id"] == str(unseen.id.value)
    reason_types = [reason["type"] for reason in items[0]["reasons"]]
    assert "collaborative_behavior" in reason_types


def test_explained_recommendations_returns_empty_list_for_an_unknown_user(
    client: TestClient,
) -> None:
    # Cold start: a well-formed but never-seen user_id, no data at all --
    # graceful fallback (200, empty), not a 404.
    response = client.get(f"/recommendations/personalized/{uuid.uuid4()}/explained")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_explained_recommendations_omit_reasons_for_signals_without_evidence(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """A book recommended only via Semantic (no recorded popularity, and no
    user_id so ALS/novelty/collaborative can't apply either) must not claim
    popularity or collaborative-behavior evidence it doesn't have -- an
    honestly partial reason list, not a fabricated complete one.
    """
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))

    response = client.get(
        f"/recommendations/personalized/{uuid.uuid4()}/explained",
        params={"book_id": str(source.id.value)},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["book"]["id"] == str(other.id.value)
    reason_types = {reason["type"] for reason in items[0]["reasons"]}
    assert reason_types == {"semantic_similarity", "novelty"}
    assert "popularity" not in reason_types
    assert "collaborative_behavior" not in reason_types


def test_explained_recommendations_reasons_have_deterministic_canonical_order(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(_valid_input())
    other = application_context.register_book_use_case.execute(_other_input())
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))
    application_context.book_popularity_repository.record(
        BookPopularity(other.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31")
    )
    user_id = uuid.uuid4()
    params = {"book_id": str(source.id.value)}

    first_response = client.get(
        f"/recommendations/personalized/{user_id}/explained", params=params
    )
    second_response = client.get(
        f"/recommendations/personalized/{user_id}/explained", params=params
    )

    first_reasons = first_response.json()["items"][0]["reasons"]
    second_reasons = second_response.json()["items"][0]["reasons"]
    assert first_reasons == second_reasons
    reason_types = [reason["type"] for reason in first_reasons]
    assert reason_types == sorted(
        reason_types,
        key=["popularity", "semantic_similarity", "collaborative_behavior", "novelty",
             "diversity"].index,
    )


def test_explained_recommendations_response_matches_personalized_recommendations_plus_reasons(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """Backward compatibility: the plain (non-explained) personalized
    endpoint's response shape is completely unaffected by this capability --
    the explained endpoint is strictly additive, a separate route.
    """
    book = application_context.register_book_use_case.execute(_valid_input())
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )
    user_id = uuid.uuid4()

    plain_response = client.get(f"/recommendations/personalized/{user_id}")
    explained_response = client.get(f"/recommendations/personalized/{user_id}/explained")

    assert plain_response.status_code == explained_response.status_code == 200
    plain_item = plain_response.json()["items"][0]
    explained_item = explained_response.json()["items"][0]
    assert "reasons" not in plain_item
    assert set(plain_item) == {"book", "score", "source"}
    assert set(explained_item) == {"book", "score", "source", "reasons"}
    assert {k: v for k, v in explained_item.items() if k != "reasons"} == plain_item
