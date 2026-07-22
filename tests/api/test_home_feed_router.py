from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext
from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.book_popularity import BookPopularity


def _register(
    application_context: ApplicationContext,
    isbn: str,
    title: str,
    category: str = "Software Engineering",
) -> Book:
    return application_context.register_book_use_case.execute(
        RegisterBookInput(isbn=isbn, title=title, author="An Author", category=category)
    )


def test_home_feed_is_empty_when_there_are_no_books(client: TestClient) -> None:
    response = client.get("/home-feed")

    assert response.status_code == 200
    assert response.json() == {"hero": None, "sections": []}


def test_home_feed_hero_is_the_top_popularity_book(
    client: TestClient, application_context: ApplicationContext
) -> None:
    minor = _register(application_context, "978-3-16-148410-0", "Minor Book")
    major = _register(application_context, "0-306-40615-2", "Major Book")
    application_context.book_popularity_repository.record(
        BookPopularity(minor.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )
    application_context.book_popularity_repository.record(
        BookPopularity(
            major.id, loan_count=100, period_start="2024-01-01", period_end="2024-01-31"
        )
    )

    response = client.get("/home-feed")

    assert response.status_code == 200
    hero = response.json()["hero"]
    assert hero["book"]["id"] == str(major.id.value)
    assert hero["score"] == 100.0
    assert hero["source"] == "popularity"


def test_home_feed_hero_includes_presentation_metadata(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = _register(application_context, "978-3-16-148410-0", "A Book")
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
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

    response = client.get("/home-feed")

    hero_book = response.json()["hero"]["book"]
    assert hero_book["publisher"] == "A Publisher"
    assert hero_book["description"] == "A description."
    assert hero_book["cover_url"] == "https://example.test/cover.jpg"
    assert hero_book["published_date"] == "2020-01-01"


def test_home_feed_falls_back_to_a_deterministic_cover_when_metadata_is_missing(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = _register(application_context, "978-3-16-148410-0", "A Book")
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )

    first_response = client.get("/home-feed")
    second_response = client.get("/home-feed")

    cover_url = first_response.json()["hero"]["book"]["cover_url"]
    assert cover_url
    assert second_response.json()["hero"]["book"]["cover_url"] == cover_url


def test_home_feed_popular_section_matches_the_popularity_endpoint(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = _register(application_context, "978-3-16-148410-0", "A Book")
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=42, period_start="2024-01-01", period_end="2024-01-31")
    )

    home_feed = client.get("/home-feed").json()
    popularity = client.get("/recommendations/popularity").json()

    popular_section = next(
        section for section in home_feed["sections"] if section["id"] == "popular"
    )
    assert [item["book"]["id"] for item in popular_section["items"]] == [
        item["book"]["id"] for item in popularity["items"]
    ]
    assert [item["score"] for item in popular_section["items"]] == [
        item["score"] for item in popularity["items"]
    ]


def test_home_feed_omits_similar_to_hero_section_when_the_hero_has_no_embedding(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = _register(application_context, "978-3-16-148410-0", "A Book")
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get("/home-feed")

    section_ids = {section["id"] for section in response.json()["sections"]}
    assert "similar-to-hero" not in section_ids


def test_home_feed_includes_similar_to_hero_section_when_the_hero_has_an_embedding(
    client: TestClient, application_context: ApplicationContext
) -> None:
    hero_book = _register(application_context, "978-3-16-148410-0", "Hero Book")
    other_book = _register(application_context, "0-306-40615-2", "Other Book")
    application_context.book_popularity_repository.record(
        BookPopularity(
            hero_book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31"
        )
    )
    application_context.generate_book_embedding_use_case.execute(str(hero_book.id.value))
    application_context.generate_book_embedding_use_case.execute(str(other_book.id.value))

    response = client.get("/home-feed")

    sections = {section["id"]: section for section in response.json()["sections"]}
    assert "similar-to-hero" in sections
    assert sections["similar-to-hero"]["title"] == "Similar to Hero Book"
    assert [item["book"]["id"] for item in sections["similar-to-hero"]["items"]] == [
        str(other_book.id.value)
    ]


def test_home_feed_groups_books_sharing_a_category_into_a_category_section(
    client: TestClient, application_context: ApplicationContext
) -> None:
    first = _register(application_context, "978-3-16-148410-0", "First", category="History")
    second = _register(application_context, "0-306-40615-2", "Second", category="History")
    for book, loan_count in ((first, 100), (second, 50)):
        application_context.book_popularity_repository.record(
            BookPopularity(book.id, loan_count, "2024-01-01", "2024-01-31")
        )

    response = client.get("/home-feed")

    sections = {section["id"]: section for section in response.json()["sections"]}
    assert "category-history" in sections
    assert sections["category-history"]["title"] == "More in History"
    assert {item["book"]["id"] for item in sections["category-history"]["items"]} == {
        str(first.id.value),
        str(second.id.value),
    }


def test_home_feed_omits_a_category_section_with_only_one_book(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book = _register(application_context, "978-3-16-148410-0", "Only Book", category="History")
    application_context.book_popularity_repository.record(
        BookPopularity(book.id, loan_count=10, period_start="2024-01-01", period_end="2024-01-31")
    )

    response = client.get("/home-feed")

    section_ids = {section["id"] for section in response.json()["sections"]}
    assert "category-history" not in section_ids


def test_home_feed_is_deterministic_across_repeated_calls(
    client: TestClient, application_context: ApplicationContext
) -> None:
    first = _register(application_context, "978-3-16-148410-0", "First", category="History")
    second = _register(application_context, "0-306-40615-2", "Second", category="History")
    for book, loan_count in ((first, 100), (second, 50)):
        application_context.book_popularity_repository.record(
            BookPopularity(book.id, loan_count, "2024-01-01", "2024-01-31")
        )

    first_response = client.get("/home-feed")
    second_response = client.get("/home-feed")

    assert first_response.json() == second_response.json()


def test_home_feed_rejects_non_positive_limit(client: TestClient) -> None:
    response = client.get("/home-feed", params={"limit": 0})

    assert response.status_code == 422


def test_home_feed_rejects_limit_above_max(client: TestClient) -> None:
    response = client.get("/home-feed", params={"limit": 101})

    assert response.status_code == 422
