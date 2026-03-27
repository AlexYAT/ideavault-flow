"""ORM table definitions for items and sessions."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Item(Base):
    """A single captured idea or note."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="inbox")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        nullable=False,
    )


class UserSession(Base):
    """Per-user bot state (e.g. current project)."""

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        onupdate=func.datetime("now"),
        nullable=False,
    )
