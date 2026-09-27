# Unit tests for app.core.payload.envelope: part of the payload contract.
import pytest

from app.core.payload.envelope import (
    MAX_CLOCK_SKEW_MS,
    from_base64url,
    is_fresh,
    is_payload_envelope,
    request_aad,
    response_aad,
    to_base64url,
)
from app.core.payload.errors import PayloadError

VALID = {"v": 1, "alg": "A256GCM", "kid": "k1", "iv": "aa", "ct": "bb", "ts": 1_700_000_000_000}


def test_base64url_round_trips_without_padding_and_reads_standard_base64() -> None:
    raw = bytes([251, 255, 191, 0, 1])
    assert "=" not in to_base64url(raw)
    assert from_base64url(to_base64url(raw)) == raw
    assert from_base64url("aGk=") == b"hi"


def test_a_value_that_is_not_base64_reads_as_tampered() -> None:
    with pytest.raises(PayloadError) as caught:
        from_base64url("a")
    assert caught.value.code == "ENVELOPE_REJECTED"


@pytest.mark.parametrize(
    "value",
    [
        None,
        "x",
        {**VALID, "v": 2},
        {**VALID, "alg": "x"},
        {**VALID, "kid": 1},
        {**VALID, "ts": 1.5},
        {**VALID, "ts": True},
    ],
)
def test_refuses_what_is_not_a_version_1_envelope(value: object) -> None:
    assert not is_payload_envelope(value)


def test_accepts_a_version_1_envelope() -> None:
    assert is_payload_envelope(VALID)


def test_freshness_holds_either_way_and_reads_the_clock_by_default() -> None:
    now = 1_700_000_000_000
    assert is_fresh(now + MAX_CLOCK_SKEW_MS, now)
    assert not is_fresh(now - MAX_CLOCK_SKEW_MS - 1, now)
    assert not is_fresh(0)


def test_aad_binds_version_method_pattern_kid_and_time() -> None:
    assert request_aad("post", "/api/notes/:id", "k1", 5) == b"1.POST./api/notes/:id.k1.5"
    assert response_aad(201, "/api/notes", "ecdh", 5) == b"1.201./api/notes.ecdh.5"
