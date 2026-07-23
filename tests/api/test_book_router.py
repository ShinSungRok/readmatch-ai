import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book_metadata import BookMetadata


def test_book_detail_returns_404_for_an_unknown_but_well_formed_id(client: TestClient) -> None:
    response = client.get(f"/books/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_book_detail_rejects_a_malformed_book_id(client: TestClient) -> None:
    response = client.get("/books/not-a-uuid")

    assert response.status_code == 400
    assert "detail" in response.json()


def test_book_detail_returns_the_book_with_presentation_metadata(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    application_context.book_metadata_repository.record(
        BookMetadata(
            book_id=book.id,
            publisher="A Publisher",
            description="A description.",
            cover_url="https://example.test/cover.jpg",
            published_date="2020-01-01",
        )
    )

    response = client.get(f"/books/{book.id.value}")

    assert response.status_code == 200
    body = response.json()
    assert body["book"]["id"] == str(book.id.value)
    assert body["book"]["isbn"] == book.isbn.value
    assert body["book"]["title"] == "A Book"
    assert body["book"]["author"] == "An Author"
    assert body["book"]["category"] == "History"
    assert body["book"]["publisher"] == "A Publisher"
    assert body["book"]["description"] == "A description."
    assert body["book"]["cover_url"] == "https://example.test/cover.jpg"
    assert body["book"]["published_date"] == "2020-01-01"
    assert body["similar_books"] == []


def test_book_detail_falls_back_to_a_deterministic_cover_when_metadata_is_missing(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )

    response = client.get(f"/books/{book.id.value}")

    assert response.status_code == 200
    assert response.json()["book"]["cover_url"]


def test_book_detail_includes_similar_books_from_semantic_similarity(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source", "An Author", "History")
    )
    other = application_context.register_book_use_case.execute(
        RegisterBookInput("0-306-40615-2", "Other", "An Author", "History")
    )
    application_context.generate_book_embedding_use_case.execute(str(source.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other.id.value))

    response = client.get(f"/books/{source.id.value}")

    assert response.status_code == 200
    similar_books = response.json()["similar_books"]
    assert len(similar_books) == 1
    assert similar_books[0]["book"]["id"] == str(other.id.value)
    assert similar_books[0]["source"] == "semantic"
    # The book itself must never appear in its own similar-books list.
    assert all(item["book"]["id"] != str(source.id.value) for item in similar_books)


def test_book_detail_respects_the_limit_parameter(
    client: TestClient, application_context: ApplicationContext
) -> None:
    source = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Source", "An Author", "History")
    )
    others = [
        application_context.register_book_use_case.execute(
            RegisterBookInput(isbn, f"Other {i}", "An Author", "History")
        )
        for i, isbn in enumerate(
            ["0-306-40615-2", "9780132350884", "978-0-13-468599-1", "978-0-596-00712-6"]
        )
    ]
    for book in [source, *others]:
        application_context.generate_book_embedding_use_case.execute(str(book.id.value))

    response = client.get(f"/books/{source.id.value}", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()["similar_books"]) == 2


def test_book_detail_rejects_non_positive_limit(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )

    response = client.get(f"/books/{book.id.value}", params={"limit": 0})

    assert response.status_code == 422


def test_search_matches_title(client: TestClient, application_context: ApplicationContext) -> None:
    application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    response = client.get("/books/search", params={"q": "clean"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Clean Code"


def test_search_matches_author_and_category(
    client: TestClient, application_context: ApplicationContext
) -> None:
    application_context.register_book_use_case.execute(
        RegisterBookInput("0-306-40615-2", "Dune", "Frank Herbert", "Science Fiction")
    )

    by_author = client.get("/books/search", params={"q": "herbert"})
    by_category = client.get("/books/search", params={"q": "science fiction"})

    assert by_author.status_code == 200
    assert len(by_author.json()["items"]) == 1
    assert by_category.status_code == 200
    assert len(by_category.json()["items"]) == 1


def test_search_includes_presentation_metadata(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )
    application_context.book_metadata_repository.record(
        BookMetadata(book_id=book.id, publisher="Prentice Hall", cover_url="https://example.test/c.jpg")
    )

    response = client.get("/books/search", params={"q": "clean"})

    item = response.json()["items"][0]
    assert item["publisher"] == "Prentice Hall"
    assert item["cover_url"] == "https://example.test/c.jpg"


def test_search_returns_empty_items_for_blank_query(
    client: TestClient, application_context: ApplicationContext
) -> None:
    application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    missing_q = client.get("/books/search")
    blank_q = client.get("/books/search", params={"q": "   "})

    assert missing_q.status_code == 200
    assert missing_q.json()["items"] == []
    assert blank_q.status_code == 200
    assert blank_q.json()["items"] == []


def test_search_returns_empty_items_when_nothing_matches(
    client: TestClient, application_context: ApplicationContext
) -> None:
    application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    response = client.get("/books/search", params={"q": "nonexistent"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_search_respects_the_limit_parameter(
    client: TestClient, application_context: ApplicationContext
) -> None:
    for i, isbn in enumerate(
        ["978-3-16-148410-0", "0-306-40615-2", "9780132350884"]
    ):
        application_context.register_book_use_case.execute(
            RegisterBookInput(isbn, f"Software Book {i}", "Author", "Software")
        )

    response = client.get("/books/search", params={"q": "software", "limit": 2})

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_search_rejects_non_positive_limit(
    client: TestClient, application_context: ApplicationContext
) -> None:
    response = client.get("/books/search", params={"q": "clean", "limit": 0})

    assert response.status_code == 422


def test_search_route_is_not_shadowed_by_the_book_id_route(
    client: TestClient, application_context: ApplicationContext
) -> None:
    """"search" must never be interpreted as a {book_id} path parameter."""
    application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "Clean Code", "Robert C. Martin", "Software")
    )

    response = client.get("/books/search", params={"q": "clean"})

    assert response.status_code == 200
    assert "items" in response.json()
