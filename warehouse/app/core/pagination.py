from typing import TypeVar

from fastapi import Query

from app.core.response import PaginationMetadata

T = TypeVar("T")


class PaginationParams:
    """Reusable FastAPI dependency for extracting and validating pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
        search: str | None = Query(None, description="Search query string"),
        sort_by: str | None = Query(None, description="Field name to sort by"),
        sort_order: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    ):
        self.page = page if isinstance(page, int) else 1
        self.page_size = page_size if isinstance(page_size, int) else 50
        self.search = search.strip() if isinstance(search, str) and search.strip() else None
        self.sort_by = sort_by.strip() if isinstance(sort_by, str) and sort_by.strip() else None
        self.sort_order = sort_order.lower() if isinstance(sort_order, str) else "asc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def build_pagination_metadata(total: int, params: PaginationParams) -> PaginationMetadata:
    """Calculate pagination metadata from total count and request parameters."""
    total_pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0
    return PaginationMetadata(
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=total_pages,
    )
