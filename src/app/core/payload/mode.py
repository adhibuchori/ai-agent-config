# The strict/off switch of the payload contract. See .claude/PAYLOAD-CONTRACT.md.
"""The switch: whether this service enforces the payload contract.

The ``PAYLOAD_MODE`` variable wins, then ``encryption`` in the committed
``payload.config.json``, then ``strict``. ``off`` exists to bisect a transport problem locally and is
refused in production, at startup, so a branch merged with the switch flipped fails to boot instead
of serving plaintext.
"""

from __future__ import annotations

from typing import Literal

# The public surface: the app wiring (settings, main) imports these.
__all__ = ["EncryptionMode", "resolve_encryption_mode"]

EncryptionMode = Literal["strict", "off"]


def resolve_encryption_mode(
    from_env: str | None, from_config: str | None, is_production: bool
) -> EncryptionMode:
    """Settles the mode from the two sources and refuses what is not allowed.

    Raises:
        ValueError: for a value that is not a mode, or ``off`` in production.
    """
    env_value = (from_env or "").strip()
    source = "PAYLOAD_MODE" if env_value else "payload.config.json encryption"
    raw = (env_value or (from_config or "").strip() or "strict").lower()
    if raw == "strict":
        return "strict"
    if raw != "off":
        raise ValueError(f'{source} must be "strict" or "off", received "{raw}"')
    if is_production:
        raise ValueError(f'{source} is "off", which is refused in production')
    return "off"
