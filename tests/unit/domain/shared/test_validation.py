"""Tests for shared domain validation helpers."""

from __future__ import annotations

import pytest

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.validation import require_non_empty


class TestRequireNonEmpty:
    """Tests for require_non_empty helper."""

    def test_valid_string_returned_stripped(self) -> None:
        """Valid non-empty string is returned with whitespace stripped."""
        result = require_non_empty("  hello world  ", field="test_field")
        assert result == "hello world"

    def test_exact_length_under_max(self) -> None:
        """String within max_length is accepted."""
        result = require_non_empty("abc", field="test_field", max_length=5)
        assert result == "abc"

    def test_exact_max_length_accepted(self) -> None:
        """String exactly equal to max_length is accepted."""
        result = require_non_empty("12345", field="test_field", max_length=5)
        assert result == "12345"

    def test_exceeding_max_length_raises_validation_error(self) -> None:
        """String exceeding max_length raises ValidationError with safe_details."""
        with pytest.raises(ValidationError) as exc_info:
            require_non_empty("123456", field="description", max_length=5)
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "validation.too_long"
        assert exc_info.value.safe_details["field"] == "description"
        assert exc_info.value.safe_details["max_length"] == "5"

    @pytest.mark.parametrize("empty_val", ["", "   ", "\t\n  \r"])
    def test_empty_or_whitespace_raises_validation_error(self, empty_val: str) -> None:
        """Empty or whitespace-only strings raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            require_non_empty(empty_val, field="name")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "validation.empty"
        assert exc_info.value.safe_details["field"] == "name"

    @pytest.mark.parametrize("non_str", [None, 123, True, False, [], {}])
    def test_non_string_input_raises_validation_error(self, non_str: object) -> None:
        """Non-string inputs raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            require_non_empty(non_str, field="title")  # type: ignore[arg-type]
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "validation.type_error"
        assert exc_info.value.safe_details["field"] == "title"

