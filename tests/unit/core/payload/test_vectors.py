# Unit tests for app.core.payload.vectors: part of the payload contract.
"""This implementation against the shared vectors every other implementation also reads.

A failure means this copy changed; never regenerate the vectors to make it pass.
"""

import json
from pathlib import Path
from typing import NotRequired, TypedDict

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.payload.envelope import from_base64url, request_aad, response_aad


class Vector(TypedDict):
    name: str
    kind: str
    method: NotRequired[str]
    status: NotRequired[int]
    pattern: str
    kid: str
    ts: int
    plaintext: object
    aad: str
    iv: str
    ct: str


class Reject(TypedDict):
    name: str
    vector: str
    aad: str


class VectorFile(TypedDict):
    testBytes: str
    vectors: list[Vector]
    rejects: list[Reject]


FILE: VectorFile = json.loads(
    Path("scripts/check/payload-vectors.json").read_text(encoding="utf-8")
)
KEY = AESGCM(from_base64url(FILE["testBytes"]))
VECTORS = {vector["name"]: vector for vector in FILE["vectors"]}


@pytest.mark.parametrize("name", list(VECTORS))
def test_builds_the_same_aad_and_opens_the_ciphertext(name: str) -> None:
    v = VECTORS[name]
    if v["kind"] == "request":
        aad = request_aad(v.get("method", ""), v["pattern"], v["kid"], v["ts"])
    else:
        aad = response_aad(v.get("status", 0), v["pattern"], v["kid"], v["ts"])
    assert aad.decode() == v["aad"]
    plain = KEY.decrypt(from_base64url(v["iv"]), from_base64url(v["ct"]), aad)
    assert json.loads(plain) == v["plaintext"]


@pytest.mark.parametrize("reject", FILE["rejects"], ids=lambda r: r["name"])
def test_refuses(reject: Reject) -> None:
    v = VECTORS[reject["vector"]]
    with pytest.raises(InvalidTag):
        KEY.decrypt(from_base64url(v["iv"]), from_base64url(v["ct"]), reject["aad"].encode())
