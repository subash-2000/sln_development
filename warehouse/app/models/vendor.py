import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EntityStatus
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.company import Company


class Vendor(BaseEntity):
    """Vendor / Supplier master entity scoped to tenant company."""

    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_vendor_company_code"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    vendor_type: Mapped[str] = mapped_column(
        String(50),
        default="SUPPLIER",
        nullable=False,
    )

    invoice_workflow: Mapped[str] = mapped_column(
        String(30),
        default="STANDARD",
        nullable=False,
        index=True,
    )

    gstin: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        index=True,
    )

    pan: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    contact_person: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    billing_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    shipping_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    payment_terms_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        lazy="joined",
    )
