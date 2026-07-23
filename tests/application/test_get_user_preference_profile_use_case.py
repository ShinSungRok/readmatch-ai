import uuid

from readmatch_ai.application.get_user_preference_profile_use_case import (
    GetUserPreferenceProfileUseCase,
)
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.preference_signal import PreferenceSignalType, UserPreferenceSignal
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)
from readmatch_ai.infrastructure.in_memory_preference_signal_repository import (
    InMemoryPreferenceSignalRepository,
)


def _setup() -> tuple[
    GetUserPreferenceProfileUseCase,
    InMemoryInteractionRepository,
    InMemoryPreferenceSignalRepository,
    InMemoryBookRepository,
]:
    book_repository = InMemoryBookRepository()
    interaction_repository = InMemoryInteractionRepository()
    signal_repository = InMemoryPreferenceSignalRepository()
    use_case = GetUserPreferenceProfileUseCase(
        interaction_repository, signal_repository, book_repository
    )
    return use_case, interaction_repository, signal_repository, book_repository


def _isbn(i: int) -> str:
    # Real, distinct, valid ISBN-13s for test fixtures.
    return ["978-3-16-148410-0", "0-306-40615-2", "9780132350884", "978-0-13-468599-1"][i]


def test_execute_returns_an_empty_profile_for_a_cold_start_user() -> None:
    use_case, *_ = _setup()

    profile = use_case.execute(str(uuid.uuid4()))

    assert profile.favorite_categories == ()
    assert profile.favorite_authors == ()
    assert profile.recent_interests == ()
    assert profile.positive_book_ids == ()
    assert profile.negative_book_ids == ()
    assert profile.recent_search_terms == ()


def test_execute_derives_favorite_categories_from_positive_interactions() -> None:
    use_case, interactions, _signals, books = _setup()
    register = RegisterBookUseCase(books)
    book_a = register.execute(RegisterBookInput(_isbn(0), "A", "Author One", "Fiction"))
    book_b = register.execute(RegisterBookInput(_isbn(1), "B", "Author Two", "Fiction"))
    book_c = register.execute(RegisterBookInput(_isbn(2), "C", "Author Three", "History"))
    user_id = UserId.generate()
    interactions.record(UserInteraction(user_id, book_a.id, InteractionType.LIKE))
    interactions.record(UserInteraction(user_id, book_b.id, InteractionType.BOOKMARK))
    interactions.record(UserInteraction(user_id, book_c.id, InteractionType.LIKE))

    profile = use_case.execute(str(user_id.value))

    assert profile.favorite_categories == ("Fiction", "History")


def test_execute_treats_read_and_rating_at_or_above_four_as_positive() -> None:
    use_case, interactions, _signals, books = _setup()
    register = RegisterBookUseCase(books)
    read_book = register.execute(RegisterBookInput(_isbn(0), "A", "Author", "Fiction"))
    rated_book = register.execute(RegisterBookInput(_isbn(1), "B", "Author", "Fiction"))
    user_id = UserId.generate()
    interactions.record(UserInteraction(user_id, read_book.id, InteractionType.READ))
    interactions.record(UserInteraction(user_id, rated_book.id, InteractionType.RATING, value=4))

    profile = use_case.execute(str(user_id.value))

    assert set(profile.positive_book_ids) == {read_book.id, rated_book.id}


def test_execute_treats_dislike_and_rating_at_or_below_two_as_negative() -> None:
    use_case, interactions, _signals, books = _setup()
    register = RegisterBookUseCase(books)
    disliked_book = register.execute(RegisterBookInput(_isbn(0), "A", "Author", "Fiction"))
    low_rated_book = register.execute(RegisterBookInput(_isbn(1), "B", "Author", "Fiction"))
    user_id = UserId.generate()
    interactions.record(UserInteraction(user_id, disliked_book.id, InteractionType.DISLIKE))
    interactions.record(
        UserInteraction(user_id, low_rated_book.id, InteractionType.RATING, value=2)
    )

    profile = use_case.execute(str(user_id.value))

    assert set(profile.negative_book_ids) == {disliked_book.id, low_rated_book.id}


def test_execute_treats_a_middling_rating_as_neither_positive_nor_negative() -> None:
    use_case, interactions, _signals, books = _setup()
    register = RegisterBookUseCase(books)
    book = register.execute(RegisterBookInput(_isbn(0), "A", "Author", "Fiction"))
    user_id = UserId.generate()
    interactions.record(UserInteraction(user_id, book.id, InteractionType.RATING, value=3))

    profile = use_case.execute(str(user_id.value))

    assert profile.positive_book_ids == ()
    assert profile.negative_book_ids == ()


def test_execute_builds_recent_interests_from_category_interest_and_viewed_books() -> None:
    use_case, interactions, signals, books = _setup()
    register = RegisterBookUseCase(books)
    viewed_book = register.execute(RegisterBookInput(_isbn(0), "A", "Author", "Science"))
    user_id = UserId.generate()
    signals.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction")
    )
    interactions.record(UserInteraction(user_id, viewed_book.id, InteractionType.VIEW))

    profile = use_case.execute(str(user_id.value))

    # The later behavioral signal (viewing a Science book) outranks the
    # earlier onboarding choice (Fiction) for recency.
    assert profile.recent_interests == ("Science", "Fiction")


def test_execute_deduplicates_recent_interests_case_insensitively() -> None:
    use_case, _interactions, signals, _books = _setup()
    user_id = UserId.generate()
    signals.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "Fiction")
    )
    signals.record(
        UserPreferenceSignal(user_id, PreferenceSignalType.CATEGORY_INTEREST, "fiction")
    )

    profile = use_case.execute(str(user_id.value))

    assert profile.recent_interests == ("fiction",)


def test_execute_returns_recent_search_terms_most_recent_first() -> None:
    use_case, _interactions, signals, _books = _setup()
    user_id = UserId.generate()
    signals.record(UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "first query"))
    signals.record(UserPreferenceSignal(user_id, PreferenceSignalType.SEARCH, "second query"))

    profile = use_case.execute(str(user_id.value))

    assert profile.recent_search_terms == ("second query", "first query")


def test_execute_skips_a_book_that_no_longer_exists() -> None:
    use_case, interactions, _signals, _books = _setup()
    user_id = UserId.generate()
    interactions.record(UserInteraction(user_id, BookId.generate(), InteractionType.LIKE))

    profile = use_case.execute(str(user_id.value))

    assert profile.favorite_categories == ()
    # The book_id itself is still recorded even though the book was
    # deleted -- only category/author derivation needs the Book to exist.
    assert len(profile.positive_book_ids) == 1
