from __future__ import annotations

from abc import ABC, abstractmethod

from readmatch_ai.domain.quality_report import RecommendationQualityReport


class RecommendationQualityReporter(ABC):
    """Port for serializing a RecommendationQualityReport into one output format.

    Deliberately format-independent at this level: concrete adapters
    (Markdown, CSV, ...) each implement `render` to produce their own
    textual representation. Keeps serialization -- and any format-specific
    library (a Markdown or CSV writer) -- entirely out of Domain/Application,
    which only ever handle the structured RecommendationQualityReport.
    """

    @abstractmethod
    def render(self, report: RecommendationQualityReport) -> str:
        """Return `report` rendered as this format's textual representation."""
