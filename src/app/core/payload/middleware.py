# The payload contract as plain ASGI middleware. See .claude/PAYLOAD-CONTRACT.md.
"""The payload contract at this service's edge, as plain ASGI (.claude/PAYLOAD-CONTRACT.md).

Opens every sealed request body before any route or validator runs, and seals every response the
registry says to seal, so no handler or service ever sees an envelope. Add it FIRST with
``add_middleware`` (which prepends), so it runs innermost: the token check and the rate limit
refuse a caller before anything is decrypted.

Two ASGI rules this file keeps: the request body is read once and replayed as one message, and
every later ``receive()`` goes to the server's own channel. Synthesising ``http.disconnect`` would
tell a streaming route its client left. A refusal raised here leaves as plaintext problem+json with
a code and no payload: the caller may hold no working key.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping

from app.core.payload.codec import open_json, parse_envelope, seal_json
from app.core.payload.envelope import ENCRYPTED_MEDIA_TYPE, KID_HEADER, request_aad, response_aad
from app.core.payload.errors import PayloadError
from app.core.payload.keys import KeyRing
from app.core.payload.mode import EncryptionMode
from app.core.payload.policy import (
    Endpoint,
    EndpointMatch,
    match_endpoint,
    seals_request,
    seals_response,
)

# The public surface: the app wiring (settings, main) imports these.
__all__ = ["PayloadMiddleware"]

Scope = MutableMapping[str, object]
Message = MutableMapping[str, object]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
App = Callable[[Scope, Receive, Send], Awaitable[None]]
_REPLACED = (b"content-type", b"content-length")


def _pairs(value: object) -> list[tuple[bytes, bytes]]:
    """ASGI headers as typed pairs; anything malformed is skipped rather than trusted."""
    pairs: list[tuple[bytes, bytes]] = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, tuple) and len(item) == 2:
            key, val = item
            if isinstance(key, bytes) and isinstance(val, bytes):
                pairs.append((key, val))
    return pairs


def _header(scope: Scope, name: str) -> str:
    for key, value in _pairs(scope.get("headers")):
        if key.decode("latin-1").lower() == name:
            return value.decode("latin-1")
    return ""


def _body(message: Message) -> bytes:
    body = message.get("body")
    return body if isinstance(body, bytes) else b""


async def _refuse(send: Send, status: int, error: PayloadError) -> None:
    detail = {
        "title": "Payload refused",
        "status": status,
        "detail": str(error),
        "code": error.code,
    }
    body = json.dumps(detail).encode()
    headers = [
        (b"content-type", b"application/problem+json"),
        (b"content-length", str(len(body)).encode()),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(_body(message))
        if not message.get("more_body"):
            return b"".join(chunks)


class PayloadMiddleware:
    """Enforces the contract for the registry it is given."""

    def __init__(
        self, app: App, *, mode: EncryptionMode, registry: dict[str, Endpoint], key_ring: KeyRing
    ) -> None:
        self.app = app
        self.mode = mode
        self.registry = registry
        self.ring = key_ring

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        method, path = scope.get("method"), scope.get("path")
        match = None
        if scope["type"] == "http" and self.mode == "strict":
            assert isinstance(method, str) and isinstance(path, str)
            match = match_endpoint(self.registry, method, path)
        if match is None:
            await self.app(scope, receive, send)
            return
        opens = seals_request(match.encryption) and match.method not in ("GET", "HEAD")
        seals = seals_response(match.encryption)
        if not (opens or seals):
            await self.app(scope, receive, send)
            return
        try:
            kid = _header(scope, KID_HEADER) or self.ring.primary.kid
            self.ring.resolve(kid)
            if opens:
                receive = await self._open(scope, receive, match)
        except PayloadError as error:
            await _refuse(send, 400, error)
            return
        await self.app(scope, receive, self._sealing(send, match, kid) if seals else send)

    async def _open(self, scope: Scope, receive: Receive, match: EndpointMatch) -> Receive:
        raw = await _read_body(receive)
        if raw and ENCRYPTED_MEDIA_TYPE not in _header(scope, "content-type"):
            route = f"{match.method} {match.pattern}"
            raise PayloadError("ENVELOPE_REQUIRED", f"{route} takes a sealed body")
        body = b""
        if raw:
            envelope = parse_envelope(raw)
            opened = open_json(
                envelope,
                key=self.ring.resolve(envelope["kid"]),
                aad_for=lambda kid, ts: request_aad(match.method, match.pattern, kid, ts),
            )
            body = json.dumps(opened).encode()
        kept = [(k, v) for k, v in _pairs(scope.get("headers")) if k.lower() not in _REPLACED]
        length = str(len(body)).encode()
        scope["headers"] = [
            *kept,
            (b"content-type", b"application/json"),
            (b"content-length", length),
        ]
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        return replay

    def _sealing(self, send: Send, match: EndpointMatch, kid: str) -> Send:
        start: Message = {}
        chunks: list[bytes] = []

        async def sealing_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                start.update(message)
                return
            chunks.append(_body(message))
            if message.get("more_body"):
                return
            status = start["status"]
            assert isinstance(status, int)
            raw = b"".join(chunks)
            if status in (204, 304) or not raw:
                await send(start)
                await send({"type": "http.response.body", "body": raw})
                return
            try:
                parsed: object = json.loads(raw)
            except ValueError:
                reason = f"{match.pattern} answered with a body that is not JSON"
                await _refuse(send, 500, PayloadError("ENVELOPE_MALFORMED", reason))
                return
            envelope = seal_json(
                parsed,
                key=self.ring.resolve(kid),
                kid=kid,
                aad_for=lambda k, ts: response_aad(status, match.pattern, k, ts),
            )
            body = json.dumps(envelope).encode()
            kept = [(k, v) for k, v in _pairs(start.get("headers")) if k.lower() not in _REPLACED]
            sealed_type = (b"content-type", ENCRYPTED_MEDIA_TYPE.encode())
            headers = [*kept, sealed_type, (b"content-length", str(len(body)).encode())]
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": body})

        return sealing_send
