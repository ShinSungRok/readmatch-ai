import uuid

from fastapi.testclient import TestClient


def test_record_preference_signal_returns_201(client: TestClient) -> None:
    user_id = str(uuid.uuid4())

    response = client.post(
        "/preference-signals",
        json={"user_id": user_id, "signal_type": "category_interest", "value": "Fiction"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "user_id": user_id,
        "signal_type": "category_interest",
        "value": "Fiction",
    }


def test_record_search_signal_returns_201(client: TestClient) -> None:
    response = client.post(
        "/preference-signals",
        json={"user_id": str(uuid.uuid4()), "signal_type": "search", "value": "healing novel"},
    )

    assert response.status_code == 201
    assert response.json()["signal_type"] == "search"


def test_record_preference_signal_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.post(
        "/preference-signals",
        json={"user_id": "not-a-uuid", "signal_type": "search", "value": "query"},
    )

    assert response.status_code == 400


def test_record_preference_signal_rejects_an_unknown_signal_type(client: TestClient) -> None:
    response = client.post(
        "/preference-signals",
        json={"user_id": str(uuid.uuid4()), "signal_type": "not-a-real-type", "value": "query"},
    )

    assert response.status_code == 400


def test_record_preference_signal_rejects_a_blank_value(client: TestClient) -> None:
    response = client.post(
        "/preference-signals",
        json={"user_id": str(uuid.uuid4()), "signal_type": "search", "value": "   "},
    )

    assert response.status_code == 400


def test_clear_preference_signal_returns_204_and_removes_the_signals(client: TestClient) -> None:
    user_id = str(uuid.uuid4())
    client.post(
        "/preference-signals",
        json={"user_id": user_id, "signal_type": "category_interest", "value": "Fiction"},
    )

    response = client.delete(
        "/preference-signals", params={"user_id": user_id, "signal_type": "category_interest"}
    )

    assert response.status_code == 204
    profile = client.get(f"/preferences/{user_id}").json()
    assert profile["recent_interests"] == []


def test_clear_preference_signal_is_a_no_op_for_a_user_with_no_signals(client: TestClient) -> None:
    response = client.delete(
        "/preference-signals",
        params={"user_id": str(uuid.uuid4()), "signal_type": "category_interest"},
    )

    assert response.status_code == 204


def test_clear_preference_signal_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.delete(
        "/preference-signals", params={"user_id": "not-a-uuid", "signal_type": "category_interest"}
    )

    assert response.status_code == 400


def test_clear_preference_signal_rejects_an_unknown_signal_type(client: TestClient) -> None:
    response = client.delete(
        "/preference-signals",
        params={"user_id": str(uuid.uuid4()), "signal_type": "not-a-real-type"},
    )

    assert response.status_code == 400
