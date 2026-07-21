from readmatch_ai.application.generate_explained_personalized_recommendation_use_case import (
    GenerateExplainedPersonalizedRecommendationUseCase,
)
from readmatch_ai.domain.book import ISBN, Author, Book, BookId, Category, Title
from readmatch_ai.domain.explainer import (
    ExplanationContext,
    ExplanationReason,
    RecommendationExplainer,
    RecommendationExplanation,
)
from readmatch_ai.domain.recommendation import (
    Recommendation,
    RecommendationItem,
    RecommendationQuery,
    RecommendationResult,
)
from readmatch_ai.domain.recommendation_engine import RecommendationEngine
from readmatch_ai.domain.user import UserId


class FakeRecommendationEngine(RecommendationEngine):
    """Mocked RecommendationEngine capturing the query it was called with."""

    def __init__(self, result: RecommendationResult) -> None:
        self._result = result
        self.received_query: RecommendationQuery | None = None

    def recommend(self, query: RecommendationQuery) -> RecommendationResult:
        self.received_query = query
        return self._result


class FakeRecommendationExplainer(RecommendationExplainer):
    """Mocked RecommendationExplainer capturing the items/context it was called with."""

    def __init__(self, explanations: list[RecommendationExplanation]) -> None:
        self._explanations = explanations
        self.received_items: list[RecommendationItem] | None = None
        self.received_context: ExplanationContext | None = None

    def explain(
        self, items: list[RecommendationItem], context: ExplanationContext
    ) -> list[RecommendationExplanation]:
        self.received_items = items
        self.received_context = context
        return self._explanations


def _book() -> Book:
    return Book(
        id=BookId.generate(),
        isbn=ISBN("978-3-16-148410-0"),
        title=Title("Clean Code"),
        author=Author("Robert C. Martin"),
        category=Category("Software Engineering"),
    )


def _item(book: Book) -> RecommendationItem:
    return RecommendationItem(book=book, score=0.8, source="hybrid")


def test_execute_builds_the_recommendation_query_from_primitives() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(engine, explainer)
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert engine.received_query == RecommendationQuery(limit=5, book_id=book_id, user_id=user_id)


def test_execute_passes_none_book_id_and_user_id_when_omitted() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(engine, explainer)

    use_case.execute(limit=5)

    assert engine.received_query == RecommendationQuery(limit=5, book_id=None, user_id=None)


def test_execute_passes_the_engines_items_and_matching_context_to_the_explainer() -> None:
    item = _item(_book())
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[item])))
    explainer = FakeRecommendationExplainer(
        [RecommendationExplanation(book_id=item.book.id, reasons=())]
    )
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(engine, explainer)
    book_id, user_id = BookId.generate(), UserId.generate()

    use_case.execute(limit=5, book_id=str(book_id.value), user_id=str(user_id.value))

    assert explainer.received_items == [item]
    assert explainer.received_context == ExplanationContext(book_id=book_id, user_id=user_id)


def test_execute_pairs_each_item_with_its_explanation_in_order() -> None:
    first, second = _item(_book()), _item(_book())
    engine = FakeRecommendationEngine(
        RecommendationResult(Recommendation(items=[first, second]))
    )
    first_explanation = RecommendationExplanation(
        book_id=first.book.id,
        reasons=(ExplanationReason(type="popularity", message="Popular with many readers."),),
    )
    second_explanation = RecommendationExplanation(book_id=second.book.id, reasons=())
    explainer = FakeRecommendationExplainer([first_explanation, second_explanation])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(engine, explainer)

    result = use_case.execute(limit=5)

    assert [explained.item for explained in result.items] == [first, second]
    assert [explained.explanation for explained in result.items] == [
        first_explanation,
        second_explanation,
    ]


def test_execute_returns_empty_result_when_engine_has_no_recommendations() -> None:
    engine = FakeRecommendationEngine(RecommendationResult(Recommendation(items=[])))
    explainer = FakeRecommendationExplainer([])
    use_case = GenerateExplainedPersonalizedRecommendationUseCase(engine, explainer)

    result = use_case.execute(limit=10)

    assert result.items == []
