import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext


def test_library_is_empty_for_a_user_with_no_interactions(client: TestClient) -> None:
    response = client.get(f"/library/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"sections": []}


def test_library_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.get("/library/not-a-uuid")

    assert response.status_code == 400


def test_library_reflects_recorded_interactions(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": str(book.id.value), "interaction_type": "bookmark"},
    )

    response = client.get(f"/library/{user_id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["sections"]) == 1
    section = body["sections"][0]
    assert section["id"] == "bookmarked"
    assert section["title"] == "Bookmarked"
    assert section["items"][0]["book"]["id"] == str(book.id.value)
    assert section["items"][0]["book"]["title"] == "A Book"
    assert section["items"][0]["interaction_type"] == "bookmark"
    assert section["items"][0]["value"] is None


def test_library_includes_rating_value(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={
            "user_id": user_id,
            "book_id": str(book.id.value),
            "interaction_type": "rating",
            "value": 4,
        },
    )

    response = client.get(f"/library/{user_id}")

    section = response.json()["sections"][0]
    assert section["id"] == "rated"
    assert section["items"][0]["value"] == 4


def test_library_no_longer_includes_a_book_after_it_is_unbookmarked(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    user_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "book_id": str(book.id.value),
        "interaction_type": "bookmark",
    }
    client.post("/interactions", json=payload)
    client.delete(
        "/interactions",
        params={"user_id": user_id, "book_id": str(book.id.value), "interaction_type": "bookmark"},
    )

    response = client.get(f"/library/{user_id}")

    assert response.json() == {"sections": []}


def test_library_sections_appear_in_a_fixed_deterministic_order(
    client: TestClient, application_context: ApplicationContext
) -> None:
    books = [
        application_context.register_book_use_case.execute(
            RegisterBookInput(isbn, f"Book {i}", "Author", "Fiction")
        )
        for i, isbn in enumerate(
            ["978-3-16-148410-0", "0-306-40615-2", "9780132350884", "978-0-13-468599-1"]
        )
    ]
    user_id = str(uuid.uuid4())
    for book, interaction_type in zip(
        books, ["disliked", "rating", "bookmark", "like"], strict=True
    ):
        payload: dict[str, str | int] = {
            "user_id": user_id,
            "book_id": str(book.id.value),
            "interaction_type": "dislike" if interaction_type == "disliked" else interaction_type,
        }
        if interaction_type == "rating":
            payload["value"] = 5
        client.post("/interactions", json=payload)

    response = client.get(f"/library/{user_id}")

    section_ids = [section["id"] for section in response.json()["sections"]]
    assert section_ids == ["liked", "bookmarked", "rated", "disliked"]
