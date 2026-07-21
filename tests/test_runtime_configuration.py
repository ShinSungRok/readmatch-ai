import pytest

from readmatch_ai.config import (
    IN_MEMORY_BACKEND,
    POSTGRESQL_BACKEND,
    ApplicationConfiguration,
    BookRepositoryConfig,
    ConfigurationViolation,
    EmbeddingGeneratorConfig,
    HybridRankingConfig,
)
from readmatch_ai.runtime_configuration import (
    COMPOSITION_FAILURE,
    CONFIGURATION_VALIDATION_FAILURE,
    STARTUP_SUCCEEDED,
    ApplicationConfigurationValidator,
    ConfigurationValidationResult,
    RuntimeBootstrapFailure,
    RuntimeBootstrapValidator,
    RuntimeConfigurationSummary,
    StartupDiagnostic,
)


def _configuration(**overrides: object) -> ApplicationConfiguration:
    defaults: dict[str, object] = {
        "mode": "development",
        "book_repository": BookRepositoryConfig(backend=IN_MEMORY_BACKEND),
        "embedding_generator": EmbeddingGeneratorConfig(backend="deterministic"),
        "hybrid_ranking": HybridRankingConfig(strategy="weighted"),
        "als_model": None,
        "parsing_violations": (),
    }
    defaults.update(overrides)
    from readmatch_ai.config import AlsModelConfig

    if defaults["als_model"] is None:
        defaults["als_model"] = AlsModelConfig()
    return ApplicationConfiguration(**defaults)  # type: ignore[arg-type]


# --- ApplicationConfigurationValidator ---


def test_validator_reports_valid_for_a_development_configuration() -> None:
    result = ApplicationConfigurationValidator().validate(_configuration())

    assert result.valid is True
    assert result.violations == ()


def test_validator_reports_valid_for_a_production_configuration_with_a_persistent_backend() -> (
    None
):
    configuration = _configuration(
        mode="production",
        book_repository=BookRepositoryConfig(
            backend=POSTGRESQL_BACKEND, database_url="postgresql://user:pass@host/db"
        ),
    )

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is True


def test_validator_rejects_production_mode_with_an_in_memory_backend() -> None:
    configuration = _configuration(mode="production")

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is False
    codes = [v.code for v in result.violations]
    assert "production_mode_requires_persistent_repository" in codes


def test_validator_allows_in_memory_backend_outside_production_mode() -> None:
    configuration = _configuration(mode="development")

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is True


def test_validator_rejects_a_database_url_with_an_invalid_scheme() -> None:
    configuration = _configuration(
        book_repository=BookRepositoryConfig(
            backend=POSTGRESQL_BACKEND, database_url="mysql://user:pass@host/db"
        )
    )

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is False
    codes = [v.code for v in result.violations]
    assert "invalid_database_url_form" in codes


def test_validator_accepts_a_valid_postgresql_database_url() -> None:
    configuration = _configuration(
        book_repository=BookRepositoryConfig(
            backend=POSTGRESQL_BACKEND, database_url="postgresql://user:pass@host/db"
        )
    )

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is True


def test_validator_never_includes_the_database_url_value_in_a_violation_message() -> None:
    configuration = _configuration(
        book_repository=BookRepositoryConfig(
            backend=POSTGRESQL_BACKEND, database_url="mysql://secret-user:secret-pass@host/db"
        )
    )

    result = ApplicationConfigurationValidator().validate(configuration)

    for violation in result.violations:
        assert "secret-pass" not in violation.message
        assert "secret-user" not in violation.message


def test_validator_aggregates_parsing_violations_with_business_rule_violations() -> None:
    parsing_violation = ConfigurationViolation(
        code="unknown_embedding_generator_backend",
        field="EMBEDDING_GENERATOR_BACKEND",
        message="Unknown backend",
    )
    configuration = _configuration(mode="production", parsing_violations=(parsing_violation,))

    result = ApplicationConfigurationValidator().validate(configuration)

    assert result.valid is False
    codes = {v.code for v in result.violations}
    assert "unknown_embedding_generator_backend" in codes
    assert "production_mode_requires_persistent_repository" in codes
    assert len(result.violations) == 2


def test_validation_result_valid_is_false_whenever_violations_are_present() -> None:
    result = ConfigurationValidationResult(
        violations=(ConfigurationViolation(code="x", field="Y", message="z"),)
    )

    assert result.valid is False


# --- RuntimeConfigurationSummary ---


def test_summary_reports_safe_adapter_categories_and_version() -> None:
    configuration = _configuration(
        embedding_generator=EmbeddingGeneratorConfig(
            backend="sentence_transformers", model_name="all-MiniLM-L6-v2"
        )
    )
    result = ConfigurationValidationResult(violations=())

    summary = RuntimeConfigurationSummary.build(configuration, result)

    assert summary.mode == "development"
    assert summary.book_repository_backend == IN_MEMORY_BACKEND
    assert summary.embedding_generator_backend == "sentence_transformers"
    assert summary.embedding_model_name == "all-MiniLM-L6-v2"
    assert summary.hybrid_ranking_strategy == "weighted"
    assert summary.observability_enabled is True
    assert summary.configuration_valid is True
    assert summary.application_version


def test_summary_never_exposes_a_database_url() -> None:
    configuration = _configuration(
        book_repository=BookRepositoryConfig(
            backend=POSTGRESQL_BACKEND, database_url="postgresql://user:pass@host/db"
        )
    )
    result = ConfigurationValidationResult(violations=())

    summary = RuntimeConfigurationSummary.build(configuration, result)

    assert "database_url" not in summary.__dataclass_fields__
    for value in summary.__dict__.values():
        assert "user:pass" not in str(value)


def test_summary_represents_a_failed_category_as_none() -> None:
    configuration = _configuration(mode=None, book_repository=None)
    result = ConfigurationValidationResult(
        violations=(ConfigurationViolation(code="unknown_runtime_mode", field="x", message="y"),)
    )

    summary = RuntimeConfigurationSummary.build(configuration, result)

    assert summary.mode is None
    assert summary.book_repository_backend is None
    assert summary.configuration_valid is False


def test_summary_field_order_is_deterministic() -> None:
    configuration = _configuration()
    result = ConfigurationValidationResult(violations=())

    summary = RuntimeConfigurationSummary.build(configuration, result)

    assert list(summary.__dataclass_fields__) == [
        "mode",
        "book_repository_backend",
        "embedding_generator_backend",
        "embedding_model_name",
        "hybrid_ranking_strategy",
        "observability_enabled",
        "configuration_valid",
        "application_version",
    ]


# --- RuntimeBootstrapValidator ---


def test_bootstrap_validator_returns_the_configuration_when_valid() -> None:
    configuration = _configuration()

    resolved = RuntimeBootstrapValidator().require_valid(configuration)

    assert resolved is configuration


def test_bootstrap_validator_raises_with_aggregated_violations_when_invalid() -> None:
    configuration = _configuration(mode="production")

    with pytest.raises(RuntimeBootstrapFailure) as exc_info:
        RuntimeBootstrapValidator().require_valid(configuration)

    assert len(exc_info.value.result.violations) == 1
    assert "production_mode_requires_persistent_repository" in str(exc_info.value)


def test_bootstrap_validator_validate_does_not_raise() -> None:
    configuration = _configuration(mode="production")

    result = RuntimeBootstrapValidator().validate(configuration)

    assert result.valid is False


def test_bootstrap_validator_is_deterministic_across_repeated_calls() -> None:
    configuration = _configuration(mode="production")
    validator = RuntimeBootstrapValidator()

    first = validator.validate(configuration)
    second = validator.validate(configuration)

    assert first == second


# --- StartupDiagnostic ---


def test_startup_diagnostic_categories_are_distinct() -> None:
    categories = {CONFIGURATION_VALIDATION_FAILURE, COMPOSITION_FAILURE, STARTUP_SUCCEEDED}

    assert len(categories) == 3


def test_startup_diagnostic_defaults_to_no_violations() -> None:
    diagnostic = StartupDiagnostic(category=STARTUP_SUCCEEDED, message="ok")

    assert diagnostic.violations == ()
