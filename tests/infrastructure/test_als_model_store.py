from pathlib import Path

import numpy as np

from readmatch_ai.domain.book import BookId
from readmatch_ai.domain.user import UserId
from readmatch_ai.infrastructure.als_model import AlsModel
from readmatch_ai.infrastructure.als_model_store import AlsModelFileStore


def _sample_model() -> AlsModel:
    return AlsModel(
        user_ids=(UserId.generate(), UserId.generate()),
        book_ids=(BookId.generate(), BookId.generate(), BookId.generate()),
        user_factors=np.array([[0.1, 0.2], [0.3, 0.4]]),
        item_factors=np.array([[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]]),
    )


def test_exists_is_false_before_saving(tmp_path: Path) -> None:
    store = AlsModelFileStore()

    assert store.exists(str(tmp_path / "model")) is False


def test_save_then_load_round_trips_the_model(tmp_path: Path) -> None:
    store = AlsModelFileStore()
    model = _sample_model()
    path = str(tmp_path / "model")

    store.save(model, path)
    loaded = store.load(path)

    assert loaded.user_ids == model.user_ids
    assert loaded.book_ids == model.book_ids
    assert np.array_equal(loaded.user_factors, model.user_factors)
    assert np.array_equal(loaded.item_factors, model.item_factors)


def test_exists_is_true_after_saving(tmp_path: Path) -> None:
    store = AlsModelFileStore()
    path = str(tmp_path / "model")

    store.save(_sample_model(), path)

    assert store.exists(path) is True


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    store = AlsModelFileStore()
    path = str(tmp_path / "nested" / "dir" / "model")

    store.save(_sample_model(), path)

    assert store.exists(path) is True


def test_path_without_npz_suffix_is_normalized_consistently(tmp_path: Path) -> None:
    store = AlsModelFileStore()
    model = _sample_model()
    path_without_suffix = str(tmp_path / "model")

    store.save(model, path_without_suffix)

    assert (tmp_path / "model.npz").exists()
    assert store.exists(path_without_suffix) is True
    loaded = store.load(path_without_suffix)
    assert loaded.user_ids == model.user_ids
