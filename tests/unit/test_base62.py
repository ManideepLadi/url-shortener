import pytest

from app.utils.base62 import decode_base62, encode_base62


class TestEncodeBase62:
    def test_zero(self):
        assert encode_base62(0) == "0"

    def test_zero_with_min_length(self):
        assert encode_base62(0, min_length=3) == "000"

    def test_small_values(self):
        assert encode_base62(1) == "1"
        assert encode_base62(61) == "z"
        assert encode_base62(62) == "10"

    def test_known_value(self):
        assert encode_base62(125) == "21"

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="non-negative"):
            encode_base62(-1)

    def test_rejects_invalid_min_length(self):
        with pytest.raises(ValueError, match="min_length"):
            encode_base62(1, min_length=0)


class TestDecodeBase62:
    def test_round_trip(self):
        for value in (0, 1, 61, 62, 125, 999_999):
            encoded = encode_base62(value)
            assert decode_base62(encoded) == value

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            decode_base62("")

    def test_rejects_invalid_character(self):
        with pytest.raises(ValueError, match="invalid base62"):
            decode_base62("abc!")
