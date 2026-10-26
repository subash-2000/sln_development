from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.constants import EntityStatus, LocationType, StorageType, WarehouseType
from app.models.base import BaseEntity


class Warehouse(BaseEntity):
    """
    Physical facility / godown master scoped to Company and optional Branch.
    """

    __tablename__ = "warehouses"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    warehouse_type = Column(String(50), default=WarehouseType.OWNED.value, nullable=False)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default="India", nullable=False)
    total_area_sqft = Column(Numeric(12, 2), nullable=True)
    total_capacity_mt = Column(Numeric(12, 2), nullable=True)
    status = Column(String(50), default=EntityStatus.ACTIVE.value, nullable=False)

    # Relationships
    company = relationship("Company", lazy="selectin")
    branch = relationship("Branch", lazy="selectin")
    locations = relationship(
        "Location",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_warehouse_company_code"),
        Index("ix_warehouses_company_status", "company_id", "status"),
    )


class Location(BaseEntity):
    """
    Hierarchical storage location node (Zone, Aisle, Rack, Shelf, Bin, Pallet Bay).
    Maintains a materialized path for efficient subtree queries and strict vendor stock isolation rules.
    """

    __tablename__ = "locations"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    location_type = Column(String(50), default=LocationType.INTERNAL.value, nullable=False)
    storage_type = Column(String(50), default=StorageType.BIN.value, nullable=False)

    # Spatial coordinates & RF Barcoding
    zone = Column(String(50), nullable=True)
    aisle = Column(String(50), nullable=True)
    rack = Column(String(50), nullable=True)
    shelf = Column(String(50), nullable=True)
    bin = Column(String(50), nullable=True)
    barcode = Column(String(100), nullable=True, index=True)

    # Capacity & physical constraints
    max_weight_kg = Column(Numeric(12, 2), nullable=True)
    max_volume_cbf = Column(Numeric(12, 2), nullable=True)
    max_pallet_capacity = Column(Integer, nullable=True)
    max_units = Column(Integer, nullable=True)
    temperature_min_celsius = Column(Numeric(5, 2), nullable=True)
    temperature_max_celsius = Column(Numeric(5, 2), nullable=True)

    # Operational & Isolation Flags
    is_scrap_location = Column(Boolean, default=False, nullable=False)
    is_quarantine_location = Column(Boolean, default=False, nullable=False)
    is_return_location = Column(Boolean, default=False, nullable=False)
    allow_mixed_products = Column(Boolean, default=True, nullable=False)
    allow_mixed_vendors = Column(
        Boolean, default=False, nullable=False
    )  # Crucial for vendor stock segregation
    is_blocked = Column(Boolean, default=False, nullable=False)
    block_reason = Column(String(255), nullable=True)
    path = Column(String(500), nullable=False, index=True)  # Materialized path
    status = Column(String(50), default=EntityStatus.ACTIVE.value, nullable=False)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="locations", lazy="selectin")
    parent = relationship(
        "Location",
        remote_side="Location.id",
        back_populates="children",
        lazy="selectin",
    )
    children = relationship(
        "Location",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "warehouse_id", "code", name="uq_location_company_wh_code"),
        UniqueConstraint("company_id", "barcode", name="uq_location_company_barcode"),
        Index("ix_locations_warehouse_type", "warehouse_id", "location_type"),
        Index("ix_locations_path", "path"),
    )
