import pytest

from app.utils.alias import generate_random_alias, validate_custom_alias


class TestGenerateRandomAlias:
    def test_length_matches_config(self):
        alias = generate_random_alias(8)
        assert len(alias) == 8

    def test_contains_only_allowed_characters(self):
        alias = generate_random_alias(12)
        assert alias.isalnum()


class TestValidateCustomAlias:
    def test_accepts_valid_alias(self):
        assert validate_custom_alias("my-link_1") == "my-link_1"

    def test_strips_whitespace(self):
        assert validate_custom_alias("  my-link  ") == "my-link"

    def test_rejects_too_short(self):
        with pytest.raises(ValueError, match="3-32 characters"):
            validate_custom_alias("ab")

    def test_rejects_invalid_characters(self):
        with pytest.raises(ValueError, match="3-32 characters"):
            validate_custom_alias("bad alias!")

    def test_rejects_reserved_alias(self):
        with pytest.raises(ValueError, match="reserved"):
            validate_custom_alias("health")
