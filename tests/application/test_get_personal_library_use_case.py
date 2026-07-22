import uuid

from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.get_personal_library_use_case import GetPersonalLibraryUseCase
from readmatch_ai.application.register_book_use_case import RegisterBookInput, RegisterBookUseCase
from readmatch_ai.domain.book import Book, BookId
from readmatch_ai.domain.interaction import InteractionType, UserInteraction
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.in_memory_book_metadata_repository import (
    InMemoryBookMetadataRepository,
)
from readmatch_ai.infrastructure.in_memory_book_repository import InMemoryBookRepository
from readmatch_ai.infrastructure.in_memory_interaction_repository import (
    InMemoryInteractionRepository,
)


def _setup() -> tuple[GetPersonalLibraryUseCase, InMemoryInteractionRepository, list[Book]]:
    book_repository = InMemoryBookRepository()
    metadata_repository = InMemoryBookMetadataRepository()
    register = RegisterBookUseCase(book_repository)
    books = [
        register.execute(RegisterBookInput("978-3-16-148410-0", "Zeta", "Author", "Fiction")),
        register.execute(RegisterBookInput("0-306-40615-2", "Alpha", "Author", "Fiction")),
        register.execute(RegisterBookInput("9780132350884", "Beta", "Author", "History")),
    ]
    interaction_repository = InMemoryInteractionRepository()
    use_case = GetPersonalLibraryUseCase(
        interaction_repository,
        GetBookPresentationUseCase(book_repository, metadata_repository),
    )
    return use_case, interaction_repository, books


def test_execute_returns_an_empty_library_for_a_user_with_no_interactions() -> None:
    use_case, _repository, _books = _setup()

    library = use_case.execute(str(uuid.uuid4()))

    assert library.sections == []


def test_execute_groups_interactions_into_the_right_sections() -> None:
    use_case, repository, books = _setup()
    user_id = UserId.generate()
    repository.record(UserInteraction(user_id, books[0].id, InteractionType.LIKE))
    repository.record(UserInteraction(user_id, books[1].id, InteractionType.BOOKMARK))
    repository.record(UserInteraction(user_id, books[2].id, InteractionType.RATING, value=4))

    library = use_case.execute(str(user_id.value))

    section_ids = [section.id for section in library.sections]
    assert section_ids == ["liked", "bookmarked", "rated"]


def test_execute_orders_items_within_a_section_deterministically_by_title() -> None:
    use_case, repository, books = _setup()
    user_id = UserId.generate()
    for book in books[:2]:
        repository.record(UserInteraction(user_id, book.id, InteractionType.LIKE))

    library = use_case.execute(str(user_id.value))

    liked_section = next(section for section in library.sections if section.id == "liked")
    titles = [item.book.title for item in liked_section.items]
    assert titles == ["Alpha", "Zeta"]


def test_execute_includes_the_rating_value_in_the_rated_section() -> None:
    use_case, repository, books = _setup()
    user_id = UserId.generate()
    repository.record(UserInteraction(user_id, books[0].id, InteractionType.RATING, value=5))

    library = use_case.execute(str(user_id.value))

    rated_section = next(section for section in library.sections if section.id == "rated")
    assert rated_section.items[0].value == 5


def test_execute_omits_click_interactions_entirely() -> None:
    use_case, repository, books = _setup()
    user_id = UserId.generate()
    repository.record(UserInteraction(user_id, books[0].id, InteractionType.CLICK))

    library = use_case.execute(str(user_id.value))

    assert library.sections == []


def test_execute_skips_a_book_that_no_longer_exists() -> None:
    use_case, repository, _books = _setup()
    user_id = UserId.generate()
    repository.record(UserInteraction(user_id, BookId.generate(), InteractionType.LIKE))

    library = use_case.execute(str(user_id.value))

    assert library.sections == []
