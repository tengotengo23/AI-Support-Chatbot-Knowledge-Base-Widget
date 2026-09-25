from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow


def new_public_key() -> str:
    return "pk_" + secrets.token_urlsafe(18)


def new_connect_code() -> str:
    return secrets.token_hex(8)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    workspaces: Mapped[list[Workspace]] = relationship(back_populates="owner")


class Workspace(Base):
    """One chatbot (one business / website). Plans are attached per workspace."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    public_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=new_public_key)

    # Bot behaviour
    bot_name: Mapped[str] = mapped_column(String(100), default="Assistant")
    welcome_message: Mapped[str] = mapped_column(Text, default="")
    company_info: Mapped[str] = mapped_column(Text, default="")
    brand_color: Mapped[str] = mapped_column(String(16), default="#2563eb")
    default_language: Mapped[str] = mapped_column(String(5), default="ka")
    lead_capture_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    handoff_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_origins: Mapped[str] = mapped_column(Text, default="")
    kb_version: Mapped[int] = mapped_column(Integer, default=0)

    # Telegram handoff
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telegram_connect_code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=new_connect_code
    )

    # Billing
    plan: Mapped[str] = mapped_column(String(20), default="free")
    plan_source: Mapped[str] = mapped_column(String(20), default="none")  # none|paddle|manual
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paddle_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paddle_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    paddle_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    paddle_cancel_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    paddle_update_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    paddle_last_event_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner: Mapped[User] = relationship(back_populates="workspaces")

    def origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in (self.allowed_origins or "").split(",") if o.strip()]


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # pdf|url|faq|text
    title: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    visitor_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(10), default="bot")  # bot|handoff
    language: Mapped[str] = mapped_column(String(5), default="ka")
    page_url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user|assistant|operator|system
    content: Mapped[str] = mapped_column(Text)
    # For user messages: True = bot answered, False = bot could not answer, None = sent to a human.
    answered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sources: Mapped[str] = mapped_column(Text, default="")  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="new")  # new|contacted|won|lost
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TelegramLink(Base):
    """Maps a Telegram message we sent to the conversation it belongs to, so that the
    business owner can simply *reply* to it in Telegram and the answer reaches the visitor."""

    __tablename__ = "telegram_links"
    __table_args__ = (UniqueConstraint("chat_id", "telegram_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    chat_id: Mapped[str] = mapped_column(String(64))
    telegram_message_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Usage(Base):
    __tablename__ = "usage"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    period: Mapped[str] = mapped_column(String(7), primary_key=True)  # YYYY-MM
    ai_messages: Mapped[int] = mapped_column(Integer, default=0)


class Invoice(Base):
    """A bank-transfer invoice issued by the platform owner. Marking it paid extends the plan.
    Buyer details and the workspace name are copied in, so the record survives workspace deletion."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_name: Mapped[str] = mapped_column(String(200), default="")
    plan: Mapped[str] = mapped_column(String(20))
    months: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="GEL")
    status: Mapped[str] = mapped_column(String(10), default="issued")  # issued|paid|void
    buyer_name: Mapped[str] = mapped_column(String(200), default="")
    buyer_tax_id: Mapped[str] = mapped_column(String(64), default="")
    buyer_email: Mapped[str] = mapped_column(String(320), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
