# Pre-shared key rings for server-to-server hops. See .claude/PAYLOAD-CONTRACT.md.
"""Pre-shared keys for server-to-server hops.

One variable holds ``kid:base64key``: a key and its id are one fact, and split across two variables
one gets rotated without the other. Pure: it parses what it is handed. The settings module is the
one place that reads the environment and passes the values in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.payload.envelope import from_base64url
from app.core.payload.errors import PayloadError

# The public surface: the app wiring (settings, main) imports these.
__all__ = ["KeyEntry", "KeyRing", "create_key_ring"]

_KID = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_KEY_BYTES = 32
ECDH_KID = "ecdh"


@dataclass(frozen=True)
class KeyEntry:
    kid: str
    key: bytes


@dataclass(frozen=True)
class KeyRing:
    """The keys one side seals with (the first) and accepts (all of them)."""

    entries: tuple[KeyEntry, ...]

    @property
    def primary(self) -> KeyEntry:
        return self.entries[0]

    def resolve(self, kid: str) -> bytes:
        """The key an envelope's ``kid`` names.

        Raises:
            PayloadError: ``ENVELOPE_KEY_UNKNOWN``: the caller seals with a key not rolled out here.
        """
        for entry in self.entries:
            if entry.kid == kid:
                return entry.key
        raise PayloadError("ENVELOPE_KEY_UNKNOWN", f'No payload key with id "{kid}"')


def _parse(value: str, name: str) -> KeyEntry:
    kid, separator, encoded = value.partition(":")
    kid = kid.strip()
    if not separator or not _KID.match(kid) or kid == ECDH_KID:
        raise ValueError(f'{name} must be "kid:base64key" with a short kid other than "{ECDH_KID}"')
    try:
        key = from_base64url(encoded)
    except PayloadError as exc:
        raise ValueError(f"{name} holds a key that is not base64") from exc
    if len(key) != _KEY_BYTES:
        raise ValueError(f"{name} must decode to {_KEY_BYTES} bytes, received {len(key)}")
    return KeyEntry(kid=kid, key=key)


def create_key_ring(sources: list[tuple[str, str | None]]) -> KeyRing:
    """Builds a ring from ``(variable name, value)`` pairs in priority order.

    An unset or blank value is skipped, so a ``_NEXT`` rotation slot needs no branch. Rotation:
    deploy both sides with the next key, then swap the order.

    Raises:
        ValueError: at startup, for a malformed value, a duplicate kid, or no key at all.
    """
    entries = tuple(_parse(value, name) for name, value in sources if value and value.strip())
    if not entries:
        first = sources[0][0] if sources else "a payload key"
        raise ValueError(f"No payload key configured; set {first}")
    kids = [entry.kid for entry in entries]
    duplicates = sorted({kid for kid in kids if kids.count(kid) > 1})
    if duplicates:
        raise ValueError(f'Two payload keys share the kid "{duplicates[0]}"')
    return KeyRing(entries=entries)
