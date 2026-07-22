from fastapi.testclient import TestClient


def test_health_response_allows_the_default_frontend_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_response_omits_cors_header_for_an_unrecognised_origin(
    client: TestClient,
) -> None:
    response = client.get("/health", headers={"Origin": "https://not-allowed.test"})

    assert "access-control-allow-origin" not in response.headers
