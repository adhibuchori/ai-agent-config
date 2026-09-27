# Unit tests for app.core.payload.policy: part of the payload contract.
from app.core.payload.policy import (
    Endpoint,
    EndpointMatch,
    match_endpoint,
    seals_request,
    seals_response,
)

REGISTRY = {
    "GET_NOTE": Endpoint("GET", "/api/notes/:id"),
    "GET_STATS": Endpoint("GET", "/api/notes/stats", "none", "public counters"),
    "GET_V1": Endpoint("GET", "/api/v1.0/items"),
}


def test_policies() -> None:
    assert [seals_request(p) for p in ("strict", "response-only", "request-only", "none")] == [
        True,
        False,
        True,
        False,
    ]
    assert [seals_response(p) for p in ("strict", "response-only", "request-only", "none")] == [
        True,
        True,
        False,
        False,
    ]


def test_the_most_specific_pattern_wins_and_literals_stay_literal() -> None:
    assert match_endpoint(REGISTRY, "get", "/api/notes/stats") == EndpointMatch(
        "GET", "/api/notes/stats", "none"
    )
    assert match_endpoint(REGISTRY, "GET", "/api/notes/7") == EndpointMatch(
        "GET", "/api/notes/:id", "strict"
    )
    assert match_endpoint(REGISTRY, "GET", "/api/v1x0/items") is None
    assert match_endpoint(REGISTRY, "DELETE", "/api/notes/7") is None
