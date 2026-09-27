# The route registry types and the policy decisions. See .claude/PAYLOAD-CONTRACT.md.
"""The route registry's types, and the one place that decides what a policy seals.

FastAPI builds its OpenAPI document at runtime, so there is no committed spec to generate the
registry from: a test walks ``app.routes`` and fails on a route the registry does not name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

EncryptionPolicy = Literal["strict", "response-only", "request-only", "none"]


@dataclass(frozen=True)
class Endpoint:
    """One registered route. ``reason`` is required for any policy but ``strict``."""

    method: str
    pattern: str
    encryption: EncryptionPolicy = "strict"
    reason: str = ""


@dataclass(frozen=True)
class EndpointMatch:
    method: str
    pattern: str
    encryption: EncryptionPolicy


def seals_request(policy: EncryptionPolicy) -> bool:
    """Whether a policy seals the request body; never compare policy strings in a transport."""
    return policy in ("strict", "request-only")


def seals_response(policy: EncryptionPolicy) -> bool:
    """Whether a policy seals the response body."""
    return policy in ("strict", "response-only")


def _matches(pattern: str, path: str) -> bool:
    parts = ["[^/]+" if part.startswith(":") else re.escape(part) for part in pattern.split("/")]
    return re.fullmatch("/".join(parts), path) is not None


def match_endpoint(registry: dict[str, Endpoint], method: str, path: str) -> EndpointMatch | None:
    """The most specific registered pattern for a request, or ``None``."""
    upper = method.upper()
    candidates = [e for e in registry.values() if e.method == upper and _matches(e.pattern, path)]
    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda e: sum(1 for part in e.pattern.split("/") if not part.startswith(":")),
    )
    return EndpointMatch(method=upper, pattern=best.pattern, encryption=best.encryption)
