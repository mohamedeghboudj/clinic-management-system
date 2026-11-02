"""Pagination primitives used by repository search methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from clinic_management.domain.shared.errors import ValidationError

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class PageRequest:
    """Encapsulates pagination parameters for a repository query.

    Attributes:
        page: 1-based page number to retrieve.
        page_size: Maximum number of items per page.
    """

    page: int
    page_size: int

    def __post_init__(self) -> None:
        """Validate that page and page_size are positive integers.

        Raises:
            ValidationError: If page or page_size are not positive integers.
        """
        if type(self.page) is not int or self.page < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="pagination.page.invalid",
                safe_details={"field": "page"},
            )
        if type(self.page_size) is not int or self.page_size < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="pagination.page_size.invalid",
                safe_details={"field": "page_size"},
            )


@dataclass(frozen=True, kw_only=True)
class Page(Generic[T]):
    """A single page of results from a paginated repository query.

    Attributes:
        items: Sequence of result items on this page.
        total: Total number of matching items across all pages.
        page: Current 1-based page number.
        page_size: Maximum items per page.
    """

    items: tuple[T, ...]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Return the total number of pages.

        Returns:
            Ceiling division of total items by page_size.
        """
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Return whether there is a subsequent page.

        Returns:
            True if the current page is not the last page.
        """
        return self.page < self.total_pages

