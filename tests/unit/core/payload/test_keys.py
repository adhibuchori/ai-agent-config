# Unit tests for app.core.payload.keys: part of the payload contract.
import pytest

from app.core.payload.envelope import to_base64url
from app.core.payload.errors import PayloadError
from app.core.payload.keys import create_key_ring

# Placeholder material for tests only: 32 bytes of one value, never a real key.
K1 = to_base64url(bytes([1]) * 32)
K2 = to_base64url(bytes([2]) * 32)


def test_first_key_seals_and_every_key_opens() -> None:
    ring = create_key_ring(
        [("A", f"k1:{K1}"), ("A_NEXT", f"k2:{K2}"), ("A_OTHER", None), ("B", " ")]
    )
    assert ring.primary.kid == "k1"
    assert ring.resolve("k2") == bytes([2]) * 32
    with pytest.raises(PayloadError) as caught:
        ring.resolve("k9")
    assert caught.value.code == "ENVELOPE_KEY_UNKNOWN"


@pytest.mark.parametrize(
    ("sources", "message"),
    [
        ([("A", "")], "set A"),
        ([], "set a payload key"),
        ([("A", K1)], 'A must be "kid:base64key"'),
        ([("A", f"ecdh:{K1}")], 'A must be "kid:base64key"'),
        ([("A", "k1:a")], "not base64"),
        ([("A", f"k1:{to_base64url(bytes(16))}")], "32 bytes, received 16"),
        ([("A", f"k1:{K1}"), ("B", f"k1:{K2}")], 'share the kid "k1"'),
    ],
)
def test_refuses_at_startup(sources: list[tuple[str, str | None]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        create_key_ring(sources)
