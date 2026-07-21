from fastapi.testclient import TestClient


def test_openapi_schema_documents_all_four_recommendation_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/recommendations/popularity" in paths
    assert "/recommendations/semantic/{book_id}" in paths
    assert "/recommendations/hybrid" in paths
    assert "/recommendations/personalized/{user_id}" in paths
    assert "get" in paths["/recommendations/popularity"]


def test_openapi_schema_declares_user_id_as_a_required_path_parameter_for_personalized(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    personalized_get = schema["paths"]["/recommendations/personalized/{user_id}"]["get"]
    parameters_by_name = {param["name"]: param for param in personalized_get["parameters"]}
    assert parameters_by_name["user_id"]["in"] == "path"
    assert parameters_by_name["user_id"]["required"] is True
    assert parameters_by_name["book_id"]["required"] is False
    assert parameters_by_name["limit"]["required"] is False


def test_openapi_schema_declares_the_recommendation_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    popularity_get = schema["paths"]["/recommendations/popularity"]["get"]
    response_content = popularity_get["responses"]["200"]["content"]
    response_schema_ref = response_content["application/json"]["schema"]
    assert "RecommendationResponse" in response_schema_ref["$ref"]
    assert "RecommendationResponse" in schema["components"]["schemas"]
    assert "RecommendationItemResponse" in schema["components"]["schemas"]
    assert "BookResponse" in schema["components"]["schemas"]


def test_docs_ui_is_served(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
