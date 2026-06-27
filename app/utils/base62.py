"""Base62 encoding and decoding for numeric identifiers."""

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(BASE62_ALPHABET)


def encode_base62(value: int, *, min_length: int = 1) -> str:
    """Encode a non-negative integer as a Base62 string."""
    if value < 0:
        raise ValueError("value must be non-negative")
    if min_length < 1:
        raise ValueError("min_length must be at least 1")

    if value == 0:
        encoded = BASE62_ALPHABET[0]
    else:
        digits: list[str] = []
        remaining = value
        while remaining > 0:
            remaining, remainder = divmod(remaining, _BASE)
            digits.append(BASE62_ALPHABET[remainder])
        encoded = "".join(reversed(digits))

    if len(encoded) < min_length:
        encoded = (BASE62_ALPHABET[0] * (min_length - len(encoded))) + encoded

    return encoded


def decode_base62(value: str) -> int:
    """Decode a Base62 string to a non-negative integer."""
    if not value:
        raise ValueError("empty base62 string")

    result = 0
    for char in value:
        try:
            digit = BASE62_ALPHABET.index(char)
        except ValueError as exc:
            raise ValueError(f"invalid base62 character: {char!r}") from exc
        result = result * _BASE + digit

    return result
