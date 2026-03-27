"""ORM table definitions for items, sessions, and RAG knowledge."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Item(Base):
    """A single captured idea or note."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="new")
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
    chat_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="vault")
    active_chat_thread_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        onupdate=func.datetime("now"),
        nullable=False,
    )


class ChatThread(Base):
    """
    Logical chat context: scoped by user + project key + mode.

    New thread on project/mode change or /resetchat; old rows stay for audit.
    """

    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        nullable=False,
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    """One turn inside a :class:`ChatThread`."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        nullable=False,
    )
    thread: Mapped[ChatThread] = relationship("ChatThread", back_populates="messages")


class VoiceRecording(Base):
    """Persisted Telegram voice file + STT outcome (audit)."""

    __tablename__ = "voice_recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_file_unique_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        nullable=False,
    )
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")


class RagDocument(Base):
    """Full ingested document (MD/TXT) before chunking."""

    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.datetime("now"),
        nullable=False,
    )
    chunks: Mapped[list[RagChunk]] = relationship(
        "RagChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class RagChunk(Base):
    """Searchable slice of a :class:`RagDocument` (FTS row); ``project`` denormalized for filters."""

    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rag_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    document: Mapped[RagDocument] = relationship("RagDocument", back_populates="chunks")


class RagGithubBinding(Base):
    """MVP GitHub raw fetch: ``owner/repo`` + branch + JSON list of paths."""

    __tablename__ = "rag_github_bindings"

    project: Mapped[str] = mapped_column(String(255), primary_key=True)
    repo_full: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(128), nullable=False, default="main")
    paths_json: Mapped[str] = mapped_column(Text, nullable=False)
