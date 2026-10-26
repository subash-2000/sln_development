import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import UOM, Product, ProductCategory, Tax, UomCategory
from app.models.rings import RingsSupplierType


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # UOM & Tax Queries
    async def list_uom_categories(self) -> list[UomCategory]:
        stmt = select(UomCategory).order_by(UomCategory.name.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_uoms(self) -> list[UOM]:
        stmt = select(UOM).options(selectinload(UOM.category)).order_by(UOM.code.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_uom_by_id(self, uom_id: uuid.UUID) -> UOM | None:
        stmt = (
            select(UOM).options(selectinload(UOM.category)).where(UOM.id == uom_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_uom_by_code(self, code: str) -> UOM | None:
        stmt = select(UOM).where(UOM.code == code)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_uom(self, uom: UOM) -> UOM:
        self.db.add(uom)
        await self.db.flush()
        return uom

    async def update_uom(self, uom: UOM) -> UOM:
        await self.db.flush()
        return uom

    async def list_taxes(self) -> list[Tax]:
        stmt = select(Tax).order_by(Tax.rate.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # Category Queries
    async def list_categories(self, company_id: uuid.UUID | None = None) -> list[ProductCategory]:
        stmt = select(ProductCategory)
        if company_id:
            stmt = stmt.where(
                or_(ProductCategory.company_id == company_id, ProductCategory.company_id.is_(None))
            )
        stmt = stmt.order_by(ProductCategory.code.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_category_by_id(self, category_id: uuid.UUID) -> ProductCategory | None:
        stmt = select(ProductCategory).where(ProductCategory.id == category_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_category(self, cat: ProductCategory) -> ProductCategory:
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def update_category(self, cat: ProductCategory) -> ProductCategory:
        await self.db.flush()
        return cat

    # Product Item Queries
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
    ) -> tuple[list[Product], int]:
        query = select(Product).options(
            selectinload(Product.company),
            selectinload(Product.category),
            selectinload(Product.uom),
            selectinload(Product.secondary_uom),
            selectinload(Product.tax),
        )
        count_query = select(func.count(Product.id))

        filters = []
        if company_id:
            filters.append(Product.company_id == company_id)

        if category_id:
            filters.append(Product.category_id == category_id)

        if vendor_id:
            filters.append(
                Product.id.in_(
                    select(RingsSupplierType.product_id).where(
                        RingsSupplierType.vendor_id == vendor_id
                    )
                )
            )

        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    Product.sku.ilike(clean_search),
                    Product.name.ilike(clean_search),
                    Product.part_number.ilike(clean_search),
                    Product.barcode.ilike(clean_search),
                    Product.hsn_code.ilike(clean_search),
                    Product.heat_number.ilike(clean_search),
                )
            )

        if status:
            filters.append(Product.status == status.strip().upper())

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        key = (sort_by or "").strip().lower()
        if key in {"category_name", "category"}:
            order_col = (
                select(ProductCategory.name)
                .where(ProductCategory.id == Product.category_id)
                .correlate(Product)
                .scalar_subquery()
            )
        elif key in {"uom_code", "uom"}:
            order_col = (
                select(UOM.code).where(UOM.id == Product.uom_id).correlate(Product).scalar_subquery()
            )
        else:
            order_col = {
                "sku": Product.sku,
                "name": Product.name,
                "part_number": Product.part_number,
                "net_weight": Product.net_weight,
                "heat_number": Product.heat_number,
                "packing_ratio": Product.packing_ratio,
                "hsn_code": Product.hsn_code,
                "hsn": Product.hsn_code,
                "status": Product.status,
                "updated_at": Product.updated_at,
                "created_at": Product.created_at,
            }.get(key, Product.name)

        if sort_order and sort_order.lower() == "desc":
            query = query.order_by(order_col.desc().nulls_last(), Product.sku.asc())
        else:
            query = query.order_by(order_col.asc().nulls_last(), Product.sku.asc())

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        products = list(result.scalars().all())
        return products, total

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        stmt = (
            select(Product)
            .options(
                selectinload(Product.company),
                selectinload(Product.category),
                selectinload(Product.uom),
                selectinload(Product.secondary_uom),
                selectinload(Product.tax),
            )
            .where(Product.id == product_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, company_id: uuid.UUID, sku: str) -> Product | None:
        stmt = select(Product).where(
            Product.company_id == company_id, Product.sku == sku.strip().upper()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, product: Product) -> Product:
        self.db.add(product)
        await self.db.flush()
        return product
