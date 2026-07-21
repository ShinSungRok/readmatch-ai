from readmatch_ai.domain.persistence_validation import (
    PersistenceRuntimeSummary,
    PersistenceValidationResult,
    PersistenceValidationViolation,
)


def test_result_is_valid_when_there_are_no_violations() -> None:
    result = PersistenceValidationResult(violations=(), checked_components=("connectivity",))

    assert result.valid is True


def test_result_is_invalid_when_violations_are_present() -> None:
    result = PersistenceValidationResult(
        violations=(
            PersistenceValidationViolation(code="x", component="y", message="z"),
        ),
        checked_components=("connectivity",),
    )

    assert result.valid is False


def test_summary_build_reports_not_applicable_for_none_result() -> None:
    summary = PersistenceRuntimeSummary.build(None)

    assert summary.applicable is False
    assert summary.valid is True
    assert summary.checked_components == ()
    assert summary.violation_count == 0


def test_summary_build_reports_a_valid_result() -> None:
    result = PersistenceValidationResult(
        violations=(),
        checked_components=("connectivity", "required_tables", "pgvector_extension"),
    )

    summary = PersistenceRuntimeSummary.build(result)

    assert summary.applicable is True
    assert summary.valid is True
    assert summary.checked_components == (
        "connectivity",
        "required_tables",
        "pgvector_extension",
    )
    assert summary.violation_count == 0


def test_summary_build_reports_an_invalid_result_with_violation_count() -> None:
    result = PersistenceValidationResult(
        violations=(
            PersistenceValidationViolation(
                code="missing_required_table", component="book_embeddings", message="missing"
            ),
            PersistenceValidationViolation(
                code="pgvector_extension_missing", component="pgvector_extension", message="missing"
            ),
        ),
        checked_components=("connectivity", "required_tables", "pgvector_extension"),
    )

    summary = PersistenceRuntimeSummary.build(result)

    assert summary.valid is False
    assert summary.violation_count == 2
