# The payload error codes. See .claude/PAYLOAD-CONTRACT.md.
"""The closed set of ways an envelope can fail to become a payload.

Codes rather than free text: they cross a process boundary as the problem+json ``code``, and the
caller maps each one to what it does next. The message is for logs; the code is for the wire.
"""

from __future__ import annotations

from typing import Literal

PayloadCode = Literal[
    "ENVELOPE_REQUIRED",
    "ENVELOPE_MALFORMED",
    "ENVELOPE_EXPIRED",
    "ENVELOPE_KEY_UNKNOWN",
    "ENVELOPE_REJECTED",
]


class PayloadError(Exception):
    """A payload failure with its code."""

    def __init__(self, code: PayloadCode, message: str) -> None:
        super().__init__(message)
        self.code: PayloadCode = code
