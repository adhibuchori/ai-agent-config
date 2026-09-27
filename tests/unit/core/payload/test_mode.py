# Unit tests for app.core.payload.mode: part of the payload contract.
import pytest

from app.core.payload.mode import resolve_encryption_mode


def test_the_variable_wins_then_the_file_then_strict() -> None:
    assert resolve_encryption_mode(" OFF ", "strict", False) == "off"
    assert resolve_encryption_mode(None, "off", False) == "off"
    assert resolve_encryption_mode("  ", None, True) == "strict"


@pytest.mark.parametrize(
    ("env", "config", "production", "message"),
    [
        ("none", None, False, "PAYLOAD_MODE"),
        (None, "lax", False, "payload.config.json"),
        (None, "off", True, "refused in production"),
    ],
)
def test_refuses(env: str | None, config: str | None, production: bool, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        resolve_encryption_mode(env, config, production)
