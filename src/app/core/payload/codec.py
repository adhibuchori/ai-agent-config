# Sealing and opening JSON envelopes with AES-256-GCM. See .claude/PAYLOAD-CONTRACT.md.
"""A JSON body into an envelope and back.

AES-256-GCM through ``cryptography``, whose ``AESGCM.encrypt`` appends the 16-byte tag to the
ciphertext: the layout WebCrypto produces, so this speaks the format with no translation step.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.payload.envelope import (
    ENVELOPE_ALG,
    ENVELOPE_VERSION,
    PayloadEnvelope,
    from_base64url,
    is_fresh,
    is_payload_envelope,
    now_ms,
    to_base64url,
)
from app.core.payload.errors import PayloadError

AadFor = Callable[[str, int], bytes]
_IV_BYTES = 12


def seal_json(body: object, *, key: bytes, kid: str, aad_for: AadFor) -> PayloadEnvelope:
    """Serialises ``body`` compactly and seals it under ``key``."""
    ts = now_ms()
    iv = os.urandom(_IV_BYTES)
    plaintext = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    sealed = AESGCM(key).encrypt(iv, plaintext, aad_for(kid, ts))
    return PayloadEnvelope(
        v=ENVELOPE_VERSION,
        alg=ENVELOPE_ALG,
        kid=kid,
        iv=to_base64url(iv),
        ct=to_base64url(sealed),
        ts=ts,
    )


def open_json(
    envelope: PayloadEnvelope, *, key: bytes, aad_for: AadFor, now: int | None = None
) -> object:
    """Checks freshness first (a replay then costs a subtraction), verifies, decrypts, parses.

    Raises:
        PayloadError: ``ENVELOPE_EXPIRED``, ``ENVELOPE_REJECTED`` or ``ENVELOPE_MALFORMED``.
    """
    if not is_fresh(envelope["ts"], now):
        raise PayloadError("ENVELOPE_EXPIRED", "Payload envelope is outside the freshness window")
    iv = from_base64url(envelope["iv"])
    if len(iv) != _IV_BYTES:
        raise PayloadError("ENVELOPE_REJECTED", "Payload authentication failed")
    try:
        plaintext = AESGCM(key).decrypt(
            iv, from_base64url(envelope["ct"]), aad_for(envelope["kid"], envelope["ts"])
        )
    except InvalidTag as exc:
        raise PayloadError("ENVELOPE_REJECTED", "Payload authentication failed") from exc
    try:
        result: object = json.loads(plaintext)
    except ValueError as exc:
        raise PayloadError("ENVELOPE_MALFORMED", "Decrypted payload is not JSON") from exc
    return result


def parse_envelope(raw: bytes | str) -> PayloadEnvelope:
    """Reads an envelope out of a raw body, or refuses it as not encrypted."""
    try:
        parsed: object = json.loads(raw)
    except ValueError as exc:
        raise PayloadError("ENVELOPE_REQUIRED", "Body is not a payload envelope") from exc
    if not is_payload_envelope(parsed):
        raise PayloadError("ENVELOPE_REQUIRED", "Body is not a payload envelope")
    return parsed
