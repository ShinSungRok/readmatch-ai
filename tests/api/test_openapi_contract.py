from fastapi.testclient import TestClient


def test_openapi_schema_documents_all_five_recommendation_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/recommendations/popularity" in paths
    assert "/recommendations/semantic/{book_id}" in paths
    assert "/recommendations/hybrid" in paths
    assert "/recommendations/personalized/{user_id}" in paths
    assert "/recommendations/personalized/{user_id}/explained" in paths
    assert "get" in paths["/recommendations/popularity"]


def test_openapi_schema_documents_explanation_reason_types_and_limitations(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    explained_get = schema["paths"]["/recommendations/personalized/{user_id}/explained"]["get"]
    description = explained_get["description"]
    for reason_type in (
        "popularity",
        "semantic_similarity",
        "collaborative_behavior",
        "novelty",
        "diversity",
    ):
        assert reason_type in description
    # Limitations: explanations are not proof of causation, and may be
    # partial/absent when evidence is limited.
    assert "not" in description.lower() and "proof" in description.lower()
    assert "no reasons" in description.lower() or "limited" in description.lower()


def test_openapi_schema_declares_user_id_as_a_required_path_parameter_for_explained(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    explained_get = schema["paths"]["/recommendations/personalized/{user_id}/explained"]["get"]
    parameters_by_name = {param["name"]: param for param in explained_get["parameters"]}
    assert parameters_by_name["user_id"]["in"] == "path"
    assert parameters_by_name["user_id"]["required"] is True
    assert parameters_by_name["book_id"]["required"] is False
    assert parameters_by_name["limit"]["required"] is False


def test_openapi_schema_declares_the_explained_recommendation_response_model(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    explained_get = schema["paths"]["/recommendations/personalized/{user_id}/explained"]["get"]
    response_schema_ref = explained_get["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert "ExplainedRecommendationResponse" in response_schema_ref["$ref"]
    schemas = schema["components"]["schemas"]
    assert "ExplainedRecommendationResponse" in schemas
    assert "ExplainedRecommendationItemResponse" in schemas
    assert "ExplanationReasonResponse" in schemas


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


def test_book_response_schema_is_unaffected_by_the_presentation_model(
    client: TestClient,
) -> None:
    """Sprint 39 adds a Book presentation model (application layer only) --
    the existing BookResponse contract embedded in every recommendation
    endpoint must stay exactly as it was, since presentation data is
    surfaced through a dedicated contract in a later Sprint, not by
    silently widening this one.
    """
    schema = client.get("/openapi.json").json()

    book_schema = schema["components"]["schemas"]["BookResponse"]
    assert set(book_schema["properties"]) == {"id", "isbn", "title", "author", "category"}


def test_docs_ui_is_served(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema_documents_the_home_feed_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/home-feed" in paths
    assert "get" in paths["/home-feed"]


def test_openapi_schema_documents_the_book_detail_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/books/{book_id}" in paths
    assert "get" in paths["/books/{book_id}"]


def test_openapi_schema_declares_the_book_detail_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    book_detail_get = schema["paths"]["/books/{book_id}"]["get"]
    response_schema = book_detail_get["responses"]["200"]["content"]["application/json"]["schema"]
    assert "BookDetailResponse" in response_schema["$ref"]
    book_detail_schema = schema["components"]["schemas"]["BookDetailResponse"]
    assert set(book_detail_schema["properties"]) == {"book", "similar_books"}


def test_openapi_schema_declares_book_id_as_a_required_path_parameter_for_book_detail(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    parameters = schema["paths"]["/books/{book_id}"]["get"]["parameters"]
    book_id_param = next(param for param in parameters if param["name"] == "book_id")
    assert book_id_param["required"] is True
    assert book_id_param["in"] == "path"


def test_openapi_schema_declares_the_home_feed_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    home_feed_get = schema["paths"]["/home-feed"]["get"]
    response_schema = home_feed_get["responses"]["200"]["content"]["application/json"]["schema"]
    assert "HomeFeedResponse" in response_schema["$ref"]
    home_feed_schema = schema["components"]["schemas"]["HomeFeedResponse"]
    assert set(home_feed_schema["properties"]) == {"hero", "sections"}
    section_schema = schema["components"]["schemas"]["HomeFeedSectionResponse"]
    assert set(section_schema["properties"]) == {"id", "title", "items"}
    item_schema = schema["components"]["schemas"]["HomeFeedItemResponse"]
    assert set(item_schema["properties"]) == {"book", "score", "source"}
    book_schema = schema["components"]["schemas"]["BookPresentationResponse"]
    assert set(book_schema["properties"]) == {
        "id",
        "isbn",
        "title",
        "author",
        "category",
        "publisher",
        "description",
        "cover_url",
        "published_date",
    }


def test_openapi_schema_documents_the_interaction_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/interactions" in paths
    assert "post" in paths["/interactions"]
    assert "delete" in paths["/interactions"]
    assert "/interactions/{user_id}" in paths
    assert "get" in paths["/interactions/{user_id}"]


def test_openapi_schema_declares_the_interaction_response_models(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    record_post = schema["paths"]["/interactions"]["post"]
    response_schema = record_post["responses"]["201"]["content"]["application/json"]["schema"]
    assert "InteractionResponse" in response_schema["$ref"]
    interaction_schema = schema["components"]["schemas"]["InteractionResponse"]
    assert set(interaction_schema["properties"]) == {
        "user_id",
        "book_id",
        "interaction_type",
        "value",
    }
    list_get = schema["paths"]["/interactions/{user_id}"]["get"]
    list_response_schema = list_get["responses"]["200"]["content"]["application/json"]["schema"]
    assert "InteractionListResponse" in list_response_schema["$ref"]
    list_schema = schema["components"]["schemas"]["InteractionListResponse"]
    assert set(list_schema["properties"]) == {"items"}


def test_openapi_schema_documents_the_library_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/library/{user_id}" in paths
    assert "get" in paths["/library/{user_id}"]


def test_openapi_schema_declares_the_library_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    library_get = schema["paths"]["/library/{user_id}"]["get"]
    response_schema = library_get["responses"]["200"]["content"]["application/json"]["schema"]
    assert "PersonalLibraryResponse" in response_schema["$ref"]
    library_schema = schema["components"]["schemas"]["PersonalLibraryResponse"]
    assert set(library_schema["properties"]) == {"sections"}
    section_schema = schema["components"]["schemas"]["LibrarySectionResponse"]
    assert set(section_schema["properties"]) == {"id", "title", "items"}
    item_schema = schema["components"]["schemas"]["LibraryItemResponse"]
    assert set(item_schema["properties"]) == {"book", "interaction_type", "value"}


def test_openapi_schema_documents_the_health_and_readiness_endpoints(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/health" in paths
    assert "/readiness" in paths
    assert "get" in paths["/health"]
    assert "get" in paths["/readiness"]


def test_openapi_schema_declares_the_health_and_readiness_response_models(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    health_response_ref = schema["paths"]["/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert "HealthResponse" in health_response_ref["$ref"]
    readiness_response_ref = schema["paths"]["/readiness"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert "ReadinessResponse" in readiness_response_ref["$ref"]
    component_schemas = schema["components"]["schemas"]
    assert "HealthResponse" in component_schemas
    assert "ReadinessResponse" in component_schemas
    assert "ComponentCheckResponse" in component_schemas
