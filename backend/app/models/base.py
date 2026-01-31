"""Base model and common imports for SQLAlchemy models."""
from datetime import datetime

from pydantic import ConfigDict
from sqlalchemy import DateTime, func, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        name = cls.__name__
        # Convert CamelCase to snake_case and pluralize
        result = []
        for i, c in enumerate(name):
            if c.isupper():
                if i > 0:
                    result.append("_")
                result.append(c.lower())
            else:
                result.append(c)
        return "".join(result) + "s"


class TimestampMixin:
    """Mixin that adds timestamp columns to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TimestampMixinNullable:
    """Mixin with nullable created_at, started_at, and optional ended_at."""

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality to models.

    This adds a deleted_at column that is set when a record is soft deleted.
    Queries can filter out soft-deleted records by checking for NULL deleted_at.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    def soft_delete(self) -> None:
        """Mark the record as deleted by setting deleted_at to now."""
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore a soft-deleted record by setting deleted_at to None."""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None
