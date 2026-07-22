from __future__ import annotations

import uuid

from readmatch_ai.application.get_book_presentation_use_case import GetBookPresentationUseCase
from readmatch_ai.application.personal_library import LibraryItem, LibrarySection, PersonalLibrary
from readmatch_ai.domain.interaction import InteractionType
from readmatch_ai.domain.interaction_repository import InteractionRepository
from readmatch_ai.domain.user import UserId

# (interaction_type, section id, section title), in this fixed, deterministic
# display order. CLICK is intentionally absent -- an ephemeral engagement
# event, not a library concept a user browses.
_LIBRARY_SECTIONS: tuple[tuple[InteractionType, str, str], ...] = (
    (InteractionType.LIKE, "liked", "Liked"),
    (InteractionType.BOOKMARK, "bookmarked", "Bookmarked"),
    (InteractionType.READ, "read", "Read"),
    (InteractionType.RATING, "rated", "Rated"),
    (InteractionType.DISLIKE, "disliked", "Disliked"),
)


class GetPersonalLibraryUseCase:
    """Composes a user's personal library from their recorded interactions.

    Reuses the existing InteractionRepository and GetBookPresentationUseCase
    (Sprint 39) -- no duplicate book or interaction storage. A book that no
    longer exists is skipped rather than raising (safe missing-book
    handling); a user with no qualifying interactions gets an empty
    library (`sections=[]`), not an error.
    """

    def __init__(
        self,
        interaction_repository: InteractionRepository,
        book_presentation_use_case: GetBookPresentationUseCase,
    ) -> None:
        self._interaction_repository = interaction_repository
        self._book_presentation_use_case = book_presentation_use_case

    def execute(self, user_id: str) -> PersonalLibrary:
        interactions = self._interaction_repository.list_by_user(UserId(uuid.UUID(user_id)))

        sections: list[LibrarySection] = []
        for interaction_type, section_id, title in _LIBRARY_SECTIONS:
            items: list[LibraryItem] = []
            for interaction in interactions:
                if interaction.interaction_type != interaction_type:
                    continue
                presentation = self._book_presentation_use_case.execute(
                    str(interaction.book_id.value)
                )
                if presentation is None:
                    continue
                items.append(
                    LibraryItem(
                        book=presentation,
                        interaction_type=interaction.interaction_type,
                        value=interaction.value,
                    )
                )
            if not items:
                continue
            # Deterministic order: by title, tie-broken by book id (matches
            # the tie-break convention already used by ranking_strategies.py
            # and reranking_policies.py).
            items.sort(key=lambda item: (item.book.title, item.book.id))
            sections.append(LibrarySection(id=section_id, title=title, items=items))

        return PersonalLibrary(sections=sections)
