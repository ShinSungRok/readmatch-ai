import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_popularity import BookPopularity


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


def test_semantic_recommendations_returns_empty_list_for_a_nonexistent_book_id(
    client: TestClient,
) -> None:
    # A well-formed but unregistered book id: no embedding can exist for it,
    # so this behaves the same as "book has no embedding yet" (200, empty),
    # not a 404 -- consistent with the underlying SemanticRecommendationEngine.
    response = client.get(f"/recommendations/semantic/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"items": []}
