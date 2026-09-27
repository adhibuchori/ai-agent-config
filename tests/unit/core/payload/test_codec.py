# Unit tests for app.core.payload.codec: part of the payload contract.
import json
import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.payload.codec import open_json, parse_envelope, seal_json
from app.core.payload.envelope import request_aad, to_base64url
from app.core.payload.errors import PayloadError

KEY = bytes([3]) * 32


def aad(kid: str, ts: int) -> bytes:
    return request_aad("POST", "/api/notes", kid, ts)


def test_round_trip() -> None:
    envelope = seal_json({"title": "x"}, key=KEY, kid="k1", aad_for=aad)
    assert envelope["kid"] == "k1"
    assert open_json(envelope, key=KEY, aad_for=aad) == {"title": "x"}


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("ts", 0, "ENVELOPE_EXPIRED"),
        ("iv", to_base64url(b"x" * 16), "ENVELOPE_REJECTED"),
        ("ct", to_base64url(b"x" * 20), "ENVELOPE_REJECTED"),
    ],
)
def test_refusals(field: str, value: object, code: str) -> None:
    envelope = seal_json({}, key=KEY, kid="k1", aad_for=aad)
    if field == "ts":
        envelope["ts"] = 0
    else:
        envelope["iv" if field == "iv" else "ct"] = str(value)
    with pytest.raises(PayloadError) as caught:
        open_json(envelope, key=KEY, aad_for=aad)
    assert caught.value.code == code


def test_plaintext_that_is_not_json_is_a_bad_envelope() -> None:
    iv = os.urandom(12)
    envelope = seal_json({}, key=KEY, kid="k1", aad_for=aad)
    ct = AESGCM(KEY).encrypt(iv, b"not json", aad("k1", envelope["ts"]))
    envelope["iv"] = to_base64url(iv)
    envelope["ct"] = to_base64url(ct)
    with pytest.raises(PayloadError) as caught:
        open_json(envelope, key=KEY, aad_for=aad)
    assert caught.value.code == "ENVELOPE_MALFORMED"


def test_parse_envelope_refuses_plaintext() -> None:
    envelope = seal_json({}, key=KEY, kid="k1", aad_for=aad)
    assert parse_envelope(json.dumps(envelope)) == envelope
    for raw in ("title=x", '{"title": "x"}'):
        with pytest.raises(PayloadError, match="not a payload envelope"):
            parse_envelope(raw)
