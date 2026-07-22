import uuid

from fastapi.testclient import TestClient

from readmatch_ai.application.register_book_use_case import RegisterBookInput
from readmatch_ai.application_context import ApplicationContext


def _register_book(application_context: ApplicationContext) -> str:
    book = application_context.register_book_use_case.execute(
        RegisterBookInput("978-3-16-148410-0", "A Book", "An Author", "History")
    )
    return str(book.id.value)


def test_record_interaction_returns_201_with_the_recorded_interaction(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)
    user_id = str(uuid.uuid4())

    response = client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": book_id, "interaction_type": "like"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "user_id": user_id,
        "book_id": book_id,
        "interaction_type": "like",
        "value": None,
    }


def test_record_rating_interaction_includes_its_value(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)

    response = client.post(
        "/interactions",
        json={
            "user_id": str(uuid.uuid4()),
            "book_id": book_id,
            "interaction_type": "rating",
            "value": 4,
        },
    )

    assert response.status_code == 201
    assert response.json()["value"] == 4


def test_record_interaction_returns_404_for_an_unknown_book(client: TestClient) -> None:
    response = client.post(
        "/interactions",
        json={
            "user_id": str(uuid.uuid4()),
            "book_id": str(uuid.uuid4()),
            "interaction_type": "like",
        },
    )

    assert response.status_code == 404


def test_record_interaction_rejects_a_malformed_book_id(client: TestClient) -> None:
    response = client.post(
        "/interactions",
        json={"user_id": str(uuid.uuid4()), "book_id": "not-a-uuid", "interaction_type": "like"},
    )

    assert response.status_code == 400


def test_record_interaction_rejects_an_unknown_interaction_type(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)

    response = client.post(
        "/interactions",
        json={
            "user_id": str(uuid.uuid4()),
            "book_id": book_id,
            "interaction_type": "not-a-real-type",
        },
    )

    assert response.status_code == 400


def test_record_interaction_rejects_an_out_of_range_rating(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)

    response = client.post(
        "/interactions",
        json={
            "user_id": str(uuid.uuid4()),
            "book_id": book_id,
            "interaction_type": "rating",
            "value": 9,
        },
    )

    assert response.status_code == 400


def test_recording_the_same_state_like_interaction_twice_is_idempotent(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)
    user_id = str(uuid.uuid4())
    payload = {"user_id": user_id, "book_id": book_id, "interaction_type": "bookmark"}

    client.post("/interactions", json=payload)
    client.post("/interactions", json=payload)

    listed = client.get(f"/interactions/{user_id}").json()["items"]
    assert len(listed) == 1


def test_click_interactions_accumulate_across_repeated_posts(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)
    user_id = str(uuid.uuid4())
    payload = {"user_id": user_id, "book_id": book_id, "interaction_type": "click"}

    client.post("/interactions", json=payload)
    client.post("/interactions", json=payload)

    listed = client.get(f"/interactions/{user_id}").json()["items"]
    assert len(listed) == 2


def test_clear_interaction_returns_204_and_removes_the_state(
    client: TestClient, application_context: ApplicationContext
) -> None:
    book_id = _register_book(application_context)
    user_id = str(uuid.uuid4())
    client.post(
        "/interactions",
        json={"user_id": user_id, "book_id": book_id, "interaction_type": "like"},
    )

    response = client.delete(
        "/interactions",
        params={"user_id": user_id, "book_id": book_id, "interaction_type": "like"},
    )

    assert response.status_code == 204
    assert client.get(f"/interactions/{user_id}").json()["items"] == []


def test_clear_interaction_is_a_no_op_for_an_interaction_that_was_never_recorded(
    client: TestClient,
) -> None:
    response = client.delete(
        "/interactions",
        params={
            "user_id": str(uuid.uuid4()),
            "book_id": str(uuid.uuid4()),
            "interaction_type": "like",
        },
    )

    assert response.status_code == 204


def test_clear_interaction_rejects_click(client: TestClient) -> None:
    response = client.delete(
        "/interactions",
        params={
            "user_id": str(uuid.uuid4()),
            "book_id": str(uuid.uuid4()),
            "interaction_type": "click",
        },
    )

    assert response.status_code == 400


def test_list_interactions_returns_empty_list_for_an_unknown_user(client: TestClient) -> None:
    response = client.get(f"/interactions/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_interactions_rejects_a_malformed_user_id(client: TestClient) -> None:
    response = client.get("/interactions/not-a-uuid")

    assert response.status_code == 400
