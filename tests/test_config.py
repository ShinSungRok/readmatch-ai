import pytest

from readmatch_ai.config import (
    DETERMINISTIC_BACKEND,
    SENTENCE_TRANSFORMERS_BACKEND,
    EmbeddingGeneratorConfig,
    UnknownEmbeddingGeneratorBackendError,
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
