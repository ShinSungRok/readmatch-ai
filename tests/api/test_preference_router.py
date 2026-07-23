import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext


def test_preferences_is_all_empty_for_a_cold_start_user(client: TestClient) -> None:
    response = client.get(f"/preferences/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {
        "favorite_categories": [],
        "favorite_authors": [],
        "recent_interests": [],
        "recent_search_terms": [],
        "positive_book_count": 0,
        "negative_book_count": 0,
    }


def test_preferences_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.get("/preferences/not-a-uuid")

    assert response.status_code == 400


def test_preferences_reflects_a_liked_books_category_and_author(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(book.id.value), "interaction_type": "like"},
    )

    response = client.get(f"/preferences/{user_id}")

    body = response.json()
    assert body["favorite_categories"] == ["History"]
    assert body["favorite_authors"] == ["An Author"]
    assert body["positive_book_count"] == 1


def test_preferences_reflects_a_recorded_search(client: TestClient) -> None:
    user_id = str(uuid.uuid4())
    client.post(
        "/preference-signals",
        json={"user_id": user_id, "signal_type": "search", "value": "healing novel"},
    )

    response = client.get(f"/preferences/{user_id}")

    assert response.json()["recent_search_terms"] == ["healing novel"]
