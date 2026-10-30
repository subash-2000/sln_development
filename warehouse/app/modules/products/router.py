import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.products.schemas import (
    ProductCategoryCreateRequest,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    TaxResponse,
    UomCategoryResponse,
    UomCreateRequest,
    UomResponse,
    UomUpdateRequest,
)
from app.modules.products.service import ProductService

router = APIRouter(tags=["Products & Master Catalogs"])


# UOM & Tax Endpoints
@router.get(
    "/uom-categories",
    response_model=StandardResponse[list[UomCategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List UOM Categories",
)
async def list_uom_categories(
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    cats = await service.list_uom_categories()
    return success_response(
        data=[c.model_dump() for c in cats], message="UOM categories retrieved successfully"
    )


@router.get(
    "/uoms",
    response_model=StandardResponse[list[UomResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Units of Measure",
)
async def list_uoms(
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    uoms = await service.list_uoms()
    return success_response(
        data=[u.model_dump() for u in uoms], message="Units of measure retrieved successfully"
    )


@router.post(
    "/uoms",
    response_model=StandardResponse[UomResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create unit of measure",
)
async def create_uom(
    request: UomCreateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    created = await service.create_uom(request)
    await db.commit()
    return success_response(data=created.model_dump(), message="UOM created successfully")


@router.get(
    "/uoms/{uom_id}",
    response_model=StandardResponse[UomResponse],
    status_code=status.HTTP_200_OK,
    summary="Get unit of measure",
)
async def get_uom(
    uom_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    uom = await service.get_uom(uom_id)
    return success_response(data=uom.model_dump(), message="UOM retrieved successfully")


@router.put(
    "/uoms/{uom_id}",
    response_model=StandardResponse[UomResponse],
    status_code=status.HTTP_200_OK,
    summary="Update unit of measure",
)
async def update_uom(
    uom_id: uuid.UUID,
    request: UomUpdateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    updated = await service.update_uom(uom_id, request)
    await db.commit()
    return success_response(data=updated.model_dump(), message="UOM updated successfully")


@router.get(
    "/taxes",
    response_model=StandardResponse[list[TaxResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Tax Rates",
)
async def list_taxes(
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    taxes = await service.list_taxes()
    return success_response(
        data=[t.model_dump() for t in taxes], message="Tax rates retrieved successfully"
    )


# Product Category Endpoints
@router.get(
    "/product-categories",
    response_model=StandardResponse[list[ProductCategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Product Categories",
)
async def list_categories(
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    cats = await service.list_categories(company_id=company_id)
    return success_response(
        data=[c.model_dump() for c in cats], message="Categories retrieved successfully"
    )


@router.post(
    "/product-categories",
    response_model=StandardResponse[ProductCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Product Category",
)
async def create_category(
    request: ProductCategoryCreateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    created = await service.create_category(request)
    return success_response(data=created.model_dump(), message="Category created successfully")


@router.get(
    "/product-categories/{category_id}",
    response_model=StandardResponse[ProductCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Product Category Details",
)
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    cat = await service.get_category(category_id)
    return success_response(data=cat.model_dump(), message="Category retrieved successfully")


@router.put(
    "/product-categories/{category_id}",
    response_model=StandardResponse[ProductCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Product Category",
)
async def update_category(
    category_id: uuid.UUID,
    request: ProductCategoryUpdateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    updated = await service.update_category(category_id, request)
    return success_response(data=updated.model_dump(), message="Category updated successfully")


@router.delete(
    "/product-categories/{category_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Product Category",
)
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    res = await service.delete_category(category_id)
    return success_response(data=res, message="Category deleted successfully")


# Product Item Endpoints
@router.get(
    "/products",
    response_model=StandardResponse[list[ProductResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Products",
)
async def list_products(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    category_id: uuid.UUID | None = Query(None, description="Filter by category"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by supplier catalog"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (ACTIVE/INACTIVE)"
    ),
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    products, total = await service.list_products(
        company_id=company_id,
        category_id=category_id,
        vendor_id=vendor_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
        sort_by=pagination.sort_by,
        sort_order=pagination.sort_order,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[p.model_dump() for p in products],
        message="Products retrieved successfully",
        pagination=meta,
    )


@router.post(
    "/products",
    response_model=StandardResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Product",
)
async def create_product(
    request: ProductCreateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    created = await service.create_product(request)
    return success_response(data=created.model_dump(), message="Product created successfully")


@router.get(
    "/products/{product_id}",
    response_model=StandardResponse[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Product Detail",
)
async def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    product = await service.get_product(product_id)
    return success_response(data=product.model_dump(), message="Product retrieved successfully")


@router.put(
    "/products/{product_id}",
    response_model=StandardResponse[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Product",
)
async def update_product(
    product_id: uuid.UUID,
    request: ProductUpdateRequest,
    current_user: User = Depends(require_permission("master.product.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    updated = await service.update_product(product_id, request)
    return success_response(data=updated.model_dump(), message="Product updated successfully")
