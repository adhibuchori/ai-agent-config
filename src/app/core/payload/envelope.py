# The envelope format, freshness and AAD builders. See .claude/PAYLOAD-CONTRACT.md.
"""The wire format: what an envelope is, and what its ciphertext is bound to.

Every constant here has a twin in each other implementation of the contract (the TypeScript
``src/lib/payload/envelope.ts`` of a frontend or a backend). A Python service answers servers only,
so the browser key-agreement header is not declared here. A change made to one and not the others
is two services that can no longer talk; the shared test vectors are what notice.
"""

from __future__ import annotations

import base64
import time
from typing import TypedDict, TypeGuard

from app.core.payload.errors import PayloadError

ENCRYPTED_MEDIA_TYPE = "application/vnd.payload-envelope+json"
ENVELOPE_VERSION = 1
ENVELOPE_ALG = "A256GCM"
KID_HEADER = "x-payload-kid"
MAX_CLOCK_SKEW_MS = 120_000


# The functional form: the keys are wire names, read by subscript, never attributes.
# The functional form: the keys are wire names, read by subscript, never as attributes.
# Functional form on purpose: the keys are wire names read by subscript, and vulture would report
# each class-syntax field that no code reads as an attribute as an unused variable.
PayloadEnvelope = TypedDict(  # noqa: UP013
    "PayloadEnvelope", {"v": int, "alg": str, "kid": str, "iv": str, "ct": str, "ts": int}
)


def to_base64url(raw: bytes) -> str:
    """Unpadded base64url, as every other implementation emits."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def from_base64url(value: str) -> bytes:
    """Decodes base64url, or standard base64 as a person pastes it.

    Raises:
        PayloadError: ``ENVELOPE_REJECTED`` for anything that is not base64: a field that does
            not decode is a tampered envelope, never an empty one.
    """
    text = value.strip().replace("+", "-").replace("/", "_").rstrip("=")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except ValueError as exc:
        raise PayloadError("ENVELOPE_REJECTED", "Malformed base64url value") from exc


def now_ms() -> int:
    """Epoch milliseconds: what ``Date.now()`` sends from the other side."""
    return int(time.time() * 1000)


def is_payload_envelope(value: object) -> TypeGuard[PayloadEnvelope]:
    """Shape only; the cipher is what verifies."""
    if not isinstance(value, dict):
        return False
    ts = value.get("ts")
    return (
        value.get("v") == ENVELOPE_VERSION
        and value.get("alg") == ENVELOPE_ALG
        and all(isinstance(value.get(field), str) for field in ("kid", "iv", "ct"))
        and isinstance(ts, int)
        and not isinstance(ts, bool)
    )


def is_fresh(ts: int, now: int | None = None) -> bool:
    """Inside the window, either way: a post-dated envelope is refused too."""
    return abs((now_ms() if now is None else now) - ts) <= MAX_CLOCK_SKEW_MS


def request_aad(method: str, pattern: str, kid: str, ts: int) -> bytes:
    """Binds a request to its method and registry pattern, never the concrete URL."""
    return f"{ENVELOPE_VERSION}.{method.upper()}.{pattern}.{kid}.{ts}".encode()


def response_aad(status: int, pattern: str, kid: str, ts: int) -> bytes:
    """Binds a response to its status and pattern; the status itself stays on the status line."""
    return f"{ENVELOPE_VERSION}.{status}.{pattern}.{kid}.{ts}".encode()
