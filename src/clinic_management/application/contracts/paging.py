"""Bounded query requests and immutable result pages."""

from dataclasses import dataclass

from clinic_management.domain.shared.errors import ValidationError

MAX_PAGE_SIZE = 100
MAX_CURSOR_LENGTH = 2048


@dataclass(frozen=True, kw_only=True)
class PageRequest:
    """Request a bounded slice; repositories validate opaque cursor contents."""

    limit: int = 25
    cursor: str | None = None

    def __post_init__(self) -> None:
        """Reject unbounded page sizes and malformed cursor containers.

        Raises:
            ValidationError: If size or cursor shape is invalid.
        """
        if type(self.limit) is not int or not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise ValidationError(code="INVALID_VALUE", message_key="paging.limit.invalid")
        if self.cursor is not None and (
            not isinstance(self.cursor, str)
            or not self.cursor
            or len(self.cursor) > MAX_CURSOR_LENGTH
            or not self.cursor.isascii()
            or any(ord(char) < 33 or ord(char) > 126 for char in self.cursor)
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="paging.cursor.invalid")


@dataclass(frozen=True, kw_only=True)
class Page[T]:
    """Return a bounded stable-order page without claiming a total row count."""

    items: tuple[T, ...]
    next_cursor: str | None

    def __post_init__(self) -> None:
        """Require an immutable bounded container and valid cursor shape.

        Raises:
            ValidationError: If the result size, container or cursor is invalid.
        """
        if not isinstance(self.items, tuple) or len(self.items) > MAX_PAGE_SIZE:
            raise ValidationError(code="INVALID_VALUE", message_key="paging.result.invalid")
        PageRequest(cursor=self.next_cursor)

    def has_next(self) -> bool:
        """Return whether the repository supplied a continuation cursor.

        Returns:
            Whether another page may be queried with the supplied cursor.
        """
        return self.next_cursor is not None
