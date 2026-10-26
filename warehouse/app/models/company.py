from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EntityStatus
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.branch import Branch


class Company(BaseEntity):
    """Company entity representing legal business operating units."""

    __tablename__ = "companies"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    gstin: Mapped[str | None] = mapped_column(
        String(15),
        index=True,
        nullable=True,
    )

    state_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    # Relationships
    branches: Mapped[list["Branch"]] = relationship(
        "Branch",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
