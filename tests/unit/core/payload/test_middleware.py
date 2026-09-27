# Unit tests for app.core.payload.middleware: part of the payload contract.
import json
from collections.abc import MutableMapping

from app.core.payload.codec import open_json, parse_envelope, seal_json
from app.core.payload.envelope import (
    ENCRYPTED_MEDIA_TYPE,
    KID_HEADER,
    request_aad,
    response_aad,
    to_base64url,
)
from app.core.payload.keys import create_key_ring
from app.core.payload.middleware import PayloadMiddleware, Receive, Send, _body, _pairs
from app.core.payload.mode import EncryptionMode
from app.core.payload.policy import Endpoint

# Test-only key material: 32 bytes of one value, never a real key.
RING = create_key_ring([("TEST_KEY", f"k1:{to_base64url(bytes([5]) * 32)}")])
REGISTRY = {
    "POST_NOTES": Endpoint("POST", "/api/notes"),
    "GET_NOTE": Endpoint("GET", "/api/notes/:id"),
    "POST_UPLOAD": Endpoint("POST", "/api/upload", "response-only", "multipart"),
    "GET_STREAM": Endpoint("GET", "/api/stream", "request-only", "event stream"),
    "GET_HEALTH": Endpoint("GET", "/health", "none", "probe"),
    "GET_TEXT": Endpoint("GET", "/api/text"),
    "DELETE_NOTE": Endpoint("DELETE", "/api/notes/:id"),
}
Message = MutableMapping[str, object]


async def echo(scope: Message, receive: Receive, send: Send) -> None:
    """A tiny app: answers with what it received, a text body, or no body, by path."""
    body = b""
    if scope["method"] not in ("GET", "HEAD"):
        first = await receive()
        body = first["body"] if isinstance(first["body"], bytes) else b""
        assert (await receive())["type"] == "http.disconnect"
    path = str(scope["path"])
    if path == "/api/text":
        status, payload = 200, b"plain"
    elif scope["method"] == "DELETE":
        status, payload = 204, b""
    else:
        status, payload = 201, json.dumps({"got": body.decode(), "path": path}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": payload[:3], "more_body": True})
    await send({"type": "http.response.body", "body": payload[3:]})


async def call(
    method: str,
    path: str,
    body: bytes | None = b"",
    headers: list[object] | None = None,
    mode: EncryptionMode = "strict",
    split: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    app = PayloadMiddleware(echo, mode=mode, registry=REGISTRY, key_ring=RING)
    sent: list[Message] = []
    first: Message = {"type": "http.request", "more_body": False}
    if body is not None:
        first["body"] = body
    queue: list[Message] = [first, {"type": "http.disconnect"}]
    if split and body:
        half = len(body) // 2
        queue[:1] = [
            {"type": "http.request", "body": body[:half], "more_body": True},
            {"type": "http.request", "body": body[half:], "more_body": False},
        ]

    async def receive() -> Message:
        return queue.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Message = {"type": "http", "method": method, "path": path}
    if headers is not None:
        scope["headers"] = headers
    await app(scope, receive, send)
    start = sent[0]
    status = start["status"]
    assert isinstance(status, int)
    out_headers = {k.decode(): v.decode() for k, v in _pairs(start["headers"])}
    return status, out_headers, b"".join(_body(m) for m in sent[1:])


def sealed(value: object, pattern: str) -> bytes:
    envelope = seal_json(
        value,
        key=RING.primary.key,
        kid="k1",
        aad_for=lambda k, t: request_aad("POST", pattern, k, t),
    )
    return json.dumps(envelope).encode()


def opened(status: int, body: bytes, pattern: str) -> object:
    return open_json(
        parse_envelope(body),
        key=RING.primary.key,
        aad_for=lambda k, t: response_aad(status, pattern, k, t),
    )


async def test_opens_a_sealed_request_and_seals_the_answer() -> None:
    headers: list[object] = [
        (b"content-type", ENCRYPTED_MEDIA_TYPE.encode()),
        (KID_HEADER.encode(), b"k1"),
        ("bad", 1),
        "x",
    ]
    status, out, body = await call(
        "POST", "/api/notes", sealed({"t": 1}, "/api/notes"), headers, split=True
    )
    assert status == 201
    assert out["content-type"] == ENCRYPTED_MEDIA_TYPE
    assert opened(status, body, "/api/notes") == {"got": '{"t": 1}', "path": "/api/notes"}


async def test_refuses_plaintext_on_a_sealed_route_and_an_unknown_key() -> None:
    status, _, body = await call(
        "POST", "/api/notes", b'{"t":1}', [(b"content-type", b"application/json")]
    )
    assert (status, json.loads(body)["code"]) == (400, "ENVELOPE_REQUIRED")
    status, _, body = await call("GET", "/api/notes/1", headers=[(KID_HEADER.encode(), b"k9")])
    assert (status, json.loads(body)["code"]) == (400, "ENVELOPE_KEY_UNKNOWN")


async def test_seals_a_bodiless_get_and_leaves_a_204_and_an_empty_post_alone() -> None:
    status, _, body = await call("GET", "/api/notes/7")
    assert opened(status, body, "/api/notes/:id") == {"got": "", "path": "/api/notes/7"}
    assert (await call("DELETE", "/api/notes/7"))[0] == 204
    status, _, body = await call("POST", "/api/notes", None, [])
    assert opened(status, body, "/api/notes") == {"got": "", "path": "/api/notes"}


async def test_half_policies_none_unregistered_and_off_pass_plaintext_through() -> None:
    status, _, body = await call("POST", "/api/upload", b"multipart")
    assert opened(status, body, "/api/upload") == {"got": "multipart", "path": "/api/upload"}
    for method, path in (("GET", "/api/stream"), ("GET", "/health"), ("GET", "/elsewhere")):
        assert json.loads((await call(method, path))[2])["path"] == path
    assert json.loads((await call("GET", "/api/notes/1", mode="off"))[2])["path"] == "/api/notes/1"


async def test_refuses_to_seal_a_body_that_is_not_json() -> None:
    status, _, body = await call("GET", "/api/text")
    assert (status, json.loads(body)["code"]) == (500, "ENVELOPE_MALFORMED")


async def test_lifespan_passes_through() -> None:
    seen: list[str] = []

    async def app(scope: Message, receive: Receive, send: Send) -> None:
        seen.append(str(scope["type"]))

    async def nothing() -> Message:
        return {}

    async def drop(message: Message) -> None:
        return None

    await PayloadMiddleware(app, mode="strict", registry=REGISTRY, key_ring=RING)(
        {"type": "lifespan"}, nothing, drop
    )
    assert seen == ["lifespan"]
