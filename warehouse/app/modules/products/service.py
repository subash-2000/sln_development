import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.models.product import UOM, Product, ProductCategory, Tax, UomCategory
from app.models.rings import RingsSupplierType
from app.models.vendor import Vendor
from app.modules.products.repository import ProductRepository
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


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)

    # UOM & Tax Services
    async def list_uom_categories(self) -> list[UomCategoryResponse]:
        cats = await self.repo.list_uom_categories()
        return [UomCategoryResponse(id=c.id, name=c.name) for c in cats]

    def _uom_to_response(
        self,
        u: UOM,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> UomResponse:
        return UomResponse(
            id=u.id,
            category_id=u.category_id,
            category_name=u.category.name if u.category else None,
            code=u.code,
            name=u.name,
            uom_type=u.uom_type,
            factor=u.factor,
            rounding_precision=u.rounding_precision,
            status=u.status,
            created_at=u.created_at,
            updated_at=u.updated_at,
            created_by_id=u.created_by_id,
            updated_by_id=u.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )

    async def list_uoms(self) -> list[UomResponse]:
        uoms = await self.repo.list_uoms()
        return [self._uom_to_response(u) for u in uoms]

    async def get_uom(self, uom_id: uuid.UUID) -> UomResponse:
        uom = await self.repo.get_uom_by_id(uom_id)
        if not uom:
            raise NotFoundException(f"UOM '{uom_id}' not found")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, uom.created_by_id, uom.updated_by_id
        )
        return self._uom_to_response(uom, created_by=created_by_name, updated_by=updated_by_name)

    async def create_uom(self, req: UomCreateRequest) -> UomResponse:
        cat = await self.db.execute(select(UomCategory).where(UomCategory.id == req.category_id))
        if not cat.scalar_one_or_none():
            raise NotFoundException(f"UOM category '{req.category_id}' not found")
        existing = await self.repo.get_uom_by_code(req.code.strip().upper())
        if existing:
            raise ConflictException(f"UOM code '{req.code}' already exists")
        uom = UOM(
            category_id=req.category_id,
            code=req.code.strip().upper(),
            name=req.name.strip(),
            uom_type=req.uom_type,
            factor=req.factor,
            rounding_precision=req.rounding_precision,
            status=req.status or EntityStatus.ACTIVE.value,
        )
        created = await self.repo.create_uom(uom)
        await self.db.refresh(created, attribute_names=["category"])
        return self._uom_to_response(created)

    async def update_uom(self, uom_id: uuid.UUID, req: UomUpdateRequest) -> UomResponse:
        uom = await self.repo.get_uom_by_id(uom_id)
        if not uom:
            raise NotFoundException(f"UOM '{uom_id}' not found")
        if req.category_id is not None:
            cat = await self.db.execute(select(UomCategory).where(UomCategory.id == req.category_id))
            if not cat.scalar_one_or_none():
                raise NotFoundException(f"UOM category '{req.category_id}' not found")
            uom.category_id = req.category_id
        if req.name is not None:
            uom.name = req.name.strip()
        if req.uom_type is not None:
            uom.uom_type = req.uom_type
        if req.factor is not None:
            uom.factor = req.factor
        if req.rounding_precision is not None:
            uom.rounding_precision = req.rounding_precision
        if req.status is not None:
            uom.status = req.status
        updated = await self.repo.update_uom(uom)
        await self.db.refresh(updated, attribute_names=["category"])
        return self._uom_to_response(updated)

    async def list_taxes(self) -> list[TaxResponse]:
        taxes = await self.repo.list_taxes()
        return [
            TaxResponse(
                id=t.id,
                code=t.code,
                name=t.name,
                tax_type=t.tax_type,
                rate=t.rate,
                description=t.description,
            )
            for t in taxes
        ]

    # Category Services
    async def list_categories(
        self, company_id: uuid.UUID | None = None
    ) -> list[ProductCategoryResponse]:
        cats = await self.repo.list_categories(company_id=company_id)
        return [
            ProductCategoryResponse(
                id=c.id,
                company_id=c.company_id,
                code=c.code,
                name=c.name,
                parent_id=c.parent_id,
                description=c.description,
                status=c.status,
            )
            for c in cats
        ]

    async def create_category(self, req: ProductCategoryCreateRequest) -> ProductCategoryResponse:
        clean_code = req.code.strip().upper()
        if req.company_id:
            c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
            if not c_res.scalar_one_or_none():
                raise NotFoundException(
                    f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
                )

        cat = ProductCategory(
            company_id=req.company_id,
            code=clean_code,
            name=req.name.strip(),
            parent_id=req.parent_id,
            description=req.description.strip() if req.description else None,
            status=EntityStatus.ACTIVE.value,
        )
        created = await self.repo.create_category(cat)
        await self.db.commit()
        self.db.expunge_all()

        full_cat = await self.repo.get_category_by_id(created.id)
        return ProductCategoryResponse(
            id=full_cat.id,
            company_id=full_cat.company_id,
            code=full_cat.code,
            name=full_cat.name,
            parent_id=full_cat.parent_id,
            description=full_cat.description,
            status=full_cat.status,
        )

    async def get_category(self, category_id: uuid.UUID) -> ProductCategoryResponse:
        cat = await self.repo.get_category_by_id(category_id)
        if not cat:
            raise NotFoundException(
                f"Product category '{category_id}' not found",
                error_code="CATEGORY_NOT_FOUND",
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, cat.created_by_id, cat.updated_by_id
        )
        return ProductCategoryResponse(
            id=cat.id,
            company_id=cat.company_id,
            code=cat.code,
            name=cat.name,
            parent_id=cat.parent_id,
            description=cat.description,
            status=cat.status,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            created_by_id=cat.created_by_id,
            updated_by_id=cat.updated_by_id,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )

    async def update_category(
        self, category_id: uuid.UUID, req: ProductCategoryUpdateRequest
    ) -> ProductCategoryResponse:
        cat = await self.repo.get_category_by_id(category_id)
        if not cat:
            raise NotFoundException(
                f"Product category '{category_id}' not found",
                error_code="CATEGORY_NOT_FOUND",
            )

        if req.name is not None:
            cat.name = req.name.strip()
        if req.parent_id is not None:
            if req.parent_id == category_id:
                raise ConflictException("Category cannot be its own parent")
            cat.parent_id = req.parent_id
        if req.description is not None:
            cat.description = req.description.strip() if req.description else None
        if req.status is not None:
            cat.status = req.status.strip().upper()

        updated = await self.repo.update_category(cat)
        await self.db.commit()
        self.db.expunge_all()

        full_cat = await self.repo.get_category_by_id(updated.id)
        return ProductCategoryResponse(
            id=full_cat.id,
            company_id=full_cat.company_id,
            code=full_cat.code,
            name=full_cat.name,
            parent_id=full_cat.parent_id,
            description=full_cat.description,
            status=full_cat.status,
        )

    async def delete_category(self, category_id: uuid.UUID) -> dict:
        cat = await self.repo.get_category_by_id(category_id)
        if not cat:
            raise NotFoundException(
                f"Product category '{category_id}' not found",
                error_code="CATEGORY_NOT_FOUND",
            )
        children_count = await self.repo.count_category_children(category_id)
        if children_count > 0:
            raise ConflictException(
                f"Cannot delete category '{cat.name}' because it has {children_count} sub-category(ies). Please reassign or delete child categories first.",
                error_code="CATEGORY_HAS_CHILDREN",
            )
        products_count = await self.repo.count_category_products(category_id)
        if products_count > 0:
            raise ConflictException(
                f"Cannot delete category '{cat.name}' because {products_count} product(s) are assigned to it. Please reassign the products first.",
                error_code="CATEGORY_HAS_PRODUCTS",
            )
        await self.repo.delete_category(cat)
        await log_audit(
            db=self.db,
            action="DELETE",
            module="products",
            entity_name="ProductCategory",
            entity_id=str(category_id),
            company_id=cat.company_id,
            old_values={"code": cat.code, "name": cat.name},
        )
        await self.db.commit()
        return {"deleted": True, "id": str(category_id), "name": cat.name}

    # Product Item Services
    async def list_products(
        self,
        company_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[ProductResponse], int]:
        products, total = await self.repo.list_products(
            company_id=company_id,
            category_id=category_id,
            vendor_id=vendor_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        vendor_map = await self._vendor_links_map([p.id for p in products])
        return [self._to_response(p, vendor_map.get(p.id, ([], []))) for p in products], total

    async def get_product(self, product_id: uuid.UUID) -> ProductResponse:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException(
                f"Product with ID '{product_id}' not found", error_code="PRODUCT_NOT_FOUND"
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, product.created_by_id, product.updated_by_id
        )
        vendor_map = await self._vendor_links_map([product.id])
        return self._to_response(
            product,
            vendor_map.get(product.id, ([], [])),
            created_by=created_by_name,
            updated_by=updated_by_name,
        )

    async def create_product(self, req: ProductCreateRequest) -> ProductResponse:
        # 1. Verify Company exists
        c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
        if not c_res.scalar_one_or_none():
            raise NotFoundException(
                f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        # 2. Check unique SKU
        clean_sku = req.sku.strip().upper()
        if await self.repo.get_by_sku(req.company_id, clean_sku):
            raise ConflictException(
                f"Product SKU '{clean_sku}' already exists in Company", error_code="SKU_EXISTS"
            )

        # 3. Verify primary UOM
        u_res = await self.db.execute(select(UOM).where(UOM.id == req.uom_id))
        if not u_res.scalar_one_or_none():
            raise NotFoundException(
                f"Primary UOM '{req.uom_id}' not found", error_code="UOM_NOT_FOUND"
            )

        # 4. Verify secondary UOM if provided
        if req.secondary_uom_id:
            su_res = await self.db.execute(select(UOM).where(UOM.id == req.secondary_uom_id))
            if not su_res.scalar_one_or_none():
                raise NotFoundException(
                    f"Secondary UOM '{req.secondary_uom_id}' not found",
                    error_code="SECONDARY_UOM_NOT_FOUND",
                )

        # 5. Verify Tax if provided
        if req.tax_id:
            t_res = await self.db.execute(select(Tax).where(Tax.id == req.tax_id))
            if not t_res.scalar_one_or_none():
                raise NotFoundException(
                    f"Tax rate '{req.tax_id}' not found", error_code="TAX_NOT_FOUND"
                )

        product = Product(
            company_id=req.company_id,
            sku=clean_sku,
            name=req.name.strip(),
            description=req.description.strip() if req.description else None,
            part_number=_strip_optional(req.part_number),
            barcode=req.barcode.strip() if req.barcode else None,
            hsn_code=req.hsn_code.strip() if req.hsn_code else None,
            category_id=req.category_id,
            uom_id=req.uom_id,
            secondary_uom_id=req.secondary_uom_id,
            uom_conversion_ratio=req.uom_conversion_ratio,
            gross_weight=req.gross_weight,
            net_weight=req.net_weight,
            weight_uom_id=req.weight_uom_id,
            length=req.length,
            width=req.width,
            height=req.height,
            volume=req.volume,
            batch_number=_strip_optional(req.batch_number),
            heat_number=_strip_optional(req.heat_number),
            gauge_number=_strip_optional(req.gauge_number),
            mill_name=_strip_optional(req.mill_name),
            package_tracking_type=req.package_tracking_type,
            package_tracking_value=_strip_optional(req.package_tracking_value),
            packing_ratio=_strip_optional(req.packing_ratio),
            is_lot_tracked=req.is_lot_tracked
            or bool(
                req.batch_number
                or req.heat_number
                or req.gauge_number
                or req.mill_name
                or req.package_tracking_type
            ),
            is_serial_tracked=req.is_serial_tracked,
            requires_expiry=req.requires_expiry,
            shelf_life_days=req.shelf_life_days,
            min_stock_level=req.min_stock_level,
            max_stock_level=req.max_stock_level,
            reorder_level=req.reorder_level,
            tax_id=req.tax_id,
            status=EntityStatus.ACTIVE.value,
        )
        created = await self.repo.create(product)
        product_id = created.id
        await self._sync_vendor_types(created, req.vendor_ids)

        await log_audit(
            db=self.db,
            action="CREATE",
            module="products",
            entity_name="Product",
            entity_id=str(product_id),
            company_id=req.company_id,
            new_values={"sku": clean_sku, "name": req.name, "company_id": str(req.company_id)},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_product = await self.repo.get_by_id(product_id)
        vendor_map = await self._vendor_links_map([product_id])
        return self._to_response(full_product, vendor_map.get(product_id, ([], [])))

    async def update_product(
        self, product_id: uuid.UUID, req: ProductUpdateRequest
    ) -> ProductResponse:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise NotFoundException(
                f"Product with ID '{product_id}' not found", error_code="PRODUCT_NOT_FOUND"
            )

        old_values = {"name": product.name, "hsn_code": product.hsn_code, "status": product.status}

        if req.name is not None:
            product.name = req.name.strip()
        if req.description is not None:
            product.description = req.description.strip() if req.description else None
        if req.part_number is not None:
            product.part_number = _strip_optional(req.part_number)
        if req.barcode is not None:
            product.barcode = req.barcode.strip() if req.barcode else None
        if req.hsn_code is not None:
            product.hsn_code = req.hsn_code.strip() if req.hsn_code else None
        if req.category_id is not None:
            product.category_id = req.category_id
        if req.secondary_uom_id is not None:
            product.secondary_uom_id = req.secondary_uom_id
        if req.uom_conversion_ratio is not None:
            product.uom_conversion_ratio = req.uom_conversion_ratio
        if req.gross_weight is not None:
            product.gross_weight = req.gross_weight
        if req.net_weight is not None:
            product.net_weight = req.net_weight
        if req.batch_number is not None:
            product.batch_number = _strip_optional(req.batch_number)
        if req.heat_number is not None:
            product.heat_number = _strip_optional(req.heat_number)
        if req.gauge_number is not None:
            product.gauge_number = _strip_optional(req.gauge_number)
        if req.mill_name is not None:
            product.mill_name = _strip_optional(req.mill_name)
        if req.package_tracking_type is not None:
            product.package_tracking_type = req.package_tracking_type or None
        if req.package_tracking_value is not None:
            product.package_tracking_value = _strip_optional(req.package_tracking_value)
        if req.packing_ratio is not None:
            product.packing_ratio = _strip_optional(req.packing_ratio)
        if req.is_lot_tracked is not None:
            product.is_lot_tracked = req.is_lot_tracked
        elif any(
            (
                req.batch_number,
                req.heat_number,
                req.gauge_number,
                req.mill_name,
                req.package_tracking_type,
            )
        ):
            product.is_lot_tracked = True
        if req.is_serial_tracked is not None:
            product.is_serial_tracked = req.is_serial_tracked
        if req.requires_expiry is not None:
            product.requires_expiry = req.requires_expiry
        if req.shelf_life_days is not None:
            product.shelf_life_days = req.shelf_life_days
        if req.min_stock_level is not None:
            product.min_stock_level = req.min_stock_level
        if req.max_stock_level is not None:
            product.max_stock_level = req.max_stock_level
        if req.reorder_level is not None:
            product.reorder_level = req.reorder_level
        if req.tax_id is not None:
            product.tax_id = req.tax_id
        if req.status is not None:
            product.status = req.status.strip().upper()
        if req.vendor_ids is not None:
            await self._sync_vendor_types(product, req.vendor_ids)

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="products",
            entity_name="Product",
            entity_id=str(product.id),
            company_id=product.company_id,
            old_values=old_values,
            new_values={"name": product.name, "status": product.status},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_product = await self.repo.get_by_id(product_id)
        vendor_map = await self._vendor_links_map([product_id])
        return self._to_response(full_product, vendor_map.get(product_id, ([], [])))

    async def _vendor_links_map(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[list[uuid.UUID], list[str]]]:
        if not product_ids:
            return {}
        rows = (
            await self.db.execute(
                select(RingsSupplierType.product_id, Vendor.id, Vendor.name)
                .join(Vendor, Vendor.id == RingsSupplierType.vendor_id)
                .where(RingsSupplierType.product_id.in_(product_ids))
                .order_by(Vendor.name.asc())
            )
        ).all()
        mapping: dict[uuid.UUID, tuple[list[uuid.UUID], list[str]]] = {}
        for product_id, vendor_id, vendor_name in rows:
            ids, names = mapping.setdefault(product_id, ([], []))
            ids.append(vendor_id)
            names.append(vendor_name)
        return mapping

    async def _sync_vendor_types(self, product: Product, vendor_ids: list[uuid.UUID] | None) -> None:
        if vendor_ids is None:
            return
        wanted = set(vendor_ids)
        if wanted:
            found = (
                await self.db.execute(
                    select(Vendor.id).where(
                        Vendor.company_id == product.company_id,
                        Vendor.id.in_(wanted),
                    )
                )
            ).scalars().all()
            wanted = set(found)
        await self.db.execute(
            delete(RingsSupplierType).where(RingsSupplierType.product_id == product.id)
        )
        for vendor_id in wanted:
            self.db.add(
                RingsSupplierType(
                    company_id=product.company_id,
                    vendor_id=vendor_id,
                    product_id=product.id,
                    per_ring_weight=product.net_weight,
                )
            )
        await self.db.flush()

    def _to_response(
        self,
        product: Product,
        vendor_link: tuple[list[uuid.UUID], list[str]] = ([], []),
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> ProductResponse:
        return ProductResponse(
            id=product.id,
            company_id=product.company_id,
            company_code=product.company.code if product.company else None,
            sku=product.sku,
            name=product.name,
            description=product.description,
            part_number=product.part_number,
            barcode=product.barcode,
            hsn_code=product.hsn_code,
            category_id=product.category_id,
            category_name=product.category.name if product.category else None,
            uom_id=product.uom_id,
            uom_code=product.uom.code if product.uom else None,
            uom_name=product.uom.name if product.uom else None,
            secondary_uom_id=product.secondary_uom_id,
            secondary_uom_code=product.secondary_uom.code if product.secondary_uom else None,
            uom_conversion_ratio=product.uom_conversion_ratio,
            gross_weight=product.gross_weight,
            net_weight=product.net_weight,
            batch_number=product.batch_number,
            heat_number=product.heat_number,
            gauge_number=product.gauge_number,
            mill_name=product.mill_name,
            package_tracking_type=product.package_tracking_type,
            package_tracking_value=product.package_tracking_value,
            packing_ratio=product.packing_ratio,
            is_lot_tracked=product.is_lot_tracked,
            is_serial_tracked=product.is_serial_tracked,
            requires_expiry=product.requires_expiry,
            shelf_life_days=product.shelf_life_days,
            min_stock_level=product.min_stock_level,
            max_stock_level=product.max_stock_level,
            reorder_level=product.reorder_level,
            tax_id=product.tax_id,
            tax_rate=product.tax.rate if product.tax else None,
            status=product.status,
            vendor_ids=vendor_link[0],
            vendor_names=vendor_link[1],
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by_id=product.created_by_id,
            updated_by_id=product.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )
