from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.logging import correlation_id_ctx

DataT = TypeVar("DataT")


class PaginationMetadata(BaseModel):
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(ge=1, description="Items per page")
    total: int = Field(ge=0, description="Total number of matching records")
    total_pages: int = Field(ge=0, description="Total pages calculated")


class StandardResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: DataT | None = None
    pagination: PaginationMetadata | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


def success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    pagination: PaginationMetadata | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    req_id = request_id or correlation_id_ctx.get()
    return {
        "success": True,
        "message": message,
        "data": data,
        "pagination": pagination.model_dump() if pagination else None,
        "request_id": req_id,
    }


def error_response(
    message: str,
    error_code: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    req_id = request_id or correlation_id_ctx.get()
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "details": details or {},
        "request_id": req_id,
    }
