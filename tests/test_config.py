import pytest

from readmatch_ai.config import (
    DETERMINISTIC_BACKEND,
    DEVELOPMENT_MODE,
    IN_MEMORY_BACKEND,
    POSTGRESQL_BACKEND,
    PRODUCTION_MODE,
    RRF_STRATEGY,
    SENTENCE_TRANSFORMERS_BACKEND,
    TEST_MODE,
    WEIGHTED_STRATEGY,
    ApplicationConfiguration,
    EmbeddingGeneratorConfig,
    HybridRankingConfig,
    UnknownEmbeddingGeneratorBackendError,
    UnknownRankingStrategyError,
)


def test_from_env_defaults_to_deterministic_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDING_GENERATOR_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL_NAME", raising=False)

    config = EmbeddingGeneratorConfig.from_env()

    assert config.backend == DETERMINISTIC_BACKEND
    assert config.model_name is None


def test_from_env_selects_sentence_transformers_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "sentence_transformers")

    config = EmbeddingGeneratorConfig.from_env()

    assert config.backend == SENTENCE_TRANSFORMERS_BACKEND


def test_from_env_reads_an_explicit_model_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "sentence_transformers")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2")

    config = EmbeddingGeneratorConfig.from_env()

    assert config.model_name == "sentence-transformers/all-mpnet-base-v2"


def test_from_env_rejects_an_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "openai")

    with pytest.raises(UnknownEmbeddingGeneratorBackendError, match="openai"):
        EmbeddingGeneratorConfig.from_env()


def test_hybrid_ranking_config_defaults_to_weighted_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HYBRID_RANKING_STRATEGY", raising=False)

    config = HybridRankingConfig.from_env()

    assert config.strategy == WEIGHTED_STRATEGY


def test_hybrid_ranking_config_selects_rrf_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_RANKING_STRATEGY", "rrf")

    config = HybridRankingConfig.from_env()

    assert config.strategy == RRF_STRATEGY


def test_hybrid_ranking_config_rejects_an_unknown_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_RANKING_STRATEGY", "borda_count")

    with pytest.raises(UnknownRankingStrategyError, match="borda_count"):
        HybridRankingConfig.from_env()


# --- Sprint 32: runtime mode and ApplicationConfiguration aggregation ---


def test_application_configuration_defaults_to_development_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)

    configuration = ApplicationConfiguration.from_env()

    assert configuration.mode == DEVELOPMENT_MODE


def test_application_configuration_reads_an_explicit_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "test")

    configuration = ApplicationConfiguration.from_env()

    assert configuration.mode == TEST_MODE


def test_application_configuration_reads_an_explicit_production_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "production")

    configuration = ApplicationConfiguration.from_env()

    assert configuration.mode == PRODUCTION_MODE


def test_application_configuration_rejects_an_unknown_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "staging")

    configuration = ApplicationConfiguration.from_env()

    assert configuration.mode is None
    assert len(configuration.parsing_violations) == 1
    violation = configuration.parsing_violations[0]
    assert violation.code == "unknown_runtime_mode"
    assert violation.field == "APPLICATION_MODE"
    assert "staging" in violation.message


def test_application_configuration_is_valid_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPLICATION_MODE", raising=False)
    monkeypatch.delenv("BOOK_REPOSITORY_BACKEND", raising=False)
    monkeypatch.delenv("EMBEDDING_GENERATOR_BACKEND", raising=False)
    monkeypatch.delenv("HYBRID_RANKING_STRATEGY", raising=False)

    configuration = ApplicationConfiguration.from_env()

    assert configuration.parsing_violations == ()
    assert configuration.book_repository is not None
    assert configuration.book_repository.backend == IN_MEMORY_BACKEND
    assert configuration.embedding_generator is not None
    assert configuration.embedding_generator.backend == DETERMINISTIC_BACKEND
    assert configuration.hybrid_ranking is not None
    assert configuration.hybrid_ranking.strategy == WEIGHTED_STRATEGY
    assert configuration.als_model is not None


def test_application_configuration_captures_a_missing_database_url_as_a_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", POSTGRESQL_BACKEND)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    configuration = ApplicationConfiguration.from_env()

    assert configuration.book_repository is None
    codes = [v.code for v in configuration.parsing_violations]
    assert "database_url_missing" in codes


def test_application_configuration_aggregates_multiple_independent_violations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "staging")
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", "not-a-backend")
    monkeypatch.setenv("EMBEDDING_GENERATOR_BACKEND", "openai")
    monkeypatch.setenv("HYBRID_RANKING_STRATEGY", "borda_count")

    configuration = ApplicationConfiguration.from_env()

    codes = {v.code for v in configuration.parsing_violations}
    assert codes == {
        "unknown_runtime_mode",
        "unknown_book_repository_backend",
        "unknown_embedding_generator_backend",
        "unknown_hybrid_ranking_strategy",
    }
    # Every independently-invalid category is still resolved to None,
    # rather than the whole aggregation stopping at the first failure.
    assert configuration.mode is None
    assert configuration.book_repository is None
    assert configuration.embedding_generator is None
    assert configuration.hybrid_ranking is None


def test_application_configuration_violation_messages_never_contain_a_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOK_REPOSITORY_BACKEND", POSTGRESQL_BACKEND)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    configuration = ApplicationConfiguration.from_env()

    for violation in configuration.parsing_violations:
        assert "://" not in violation.message


def test_application_configuration_from_env_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_MODE", "staging")

    first = ApplicationConfiguration.from_env()
    second = ApplicationConfiguration.from_env()

    assert first == second
